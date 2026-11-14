"""Synthetic behavioral fixtures; no models, network, or benchmark measurements."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fast_screen as screen

QUOTE = 'A concrete passage long enough for the checked quote.'


class FastScreenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checklist = {'task_id': 't1', 'items': [
            {'id': 'a', 'text': 'State the concrete passage.'},
            {'id': 'b', 'text': 'State another requirement.'}]}
        self.checklist_path = self.write('checklist.json', self.checklist)
        self.answer = self.root / 'answer.txt'
        self.answer.write_bytes(QUOTE.encode())
        self.reply = self.root / 'reply.json'
        self.screen_path = self.root / 'screen.json'

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        return path

    def cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = screen.main(list(map(str, args)))
        return code, output.getvalue()

    def json_cli(self, *args):
        code, output = self.cli(*args, '--format', 'json')
        return code, json.loads(output)

    def labels(self, rows=None, *, raw=None, extra=()):
        if raw is not None:
            self.reply.write_bytes(raw)
        else:
            self.write('reply.json', {'items': rows if rows is not None else [
                {'id': 'a', 'label': 'yes', 'quote': QUOTE}, {'id': 'b', 'label': 'no'}]})
        return self.json_cli('labels', '--checklist', self.checklist_path, '--answer', self.answer,
                             '--reply', self.reply, *extra)

    def fixture(self, native=None, food=None):
        native = native if native is not None else [['no'], ['no'], ['yes']]
        food = food if food is not None else [['yes'], ['yes'], ['yes']]
        value = {'food': 'synthetic food', 'static': {'status': 'clear', 'reason': ''}, 'tasks': []}
        for index, (base, candidate) in enumerate(zip(native, food), 1):
            task_id = 't' + str(index)
            task = {'id': task_id}
            checklist = {'task_id': task_id, 'items': [
                {'id': str(i), 'text': 'Synthetic requirement ' + str(i)} for i in range(len(base))]}
            checklist_bytes = json.dumps(checklist).encode()
            for arm, labels in (('native', base), ('food', candidate)):
                if labels is None:
                    task[arm] = None
                    continue
                rows = [{'id': str(i), 'label': label, 'quote': QUOTE if label == 'yes' else ''}
                        for i, label in enumerate(labels)]
                checked = screen.checked_labels(checklist, hashlib.sha256(checklist_bytes).hexdigest(),
                                                QUOTE.encode(), json.dumps({'items': rows}).encode())
                path = self.write(task_id + '-' + arm + '.json', checked)
                task[arm] = {'labels': path.name, 'logical_tokens': 100 if arm == 'native' else 150,
                             'seconds': 10, 'family': 'fixture-family'}
            value['tasks'].append(task)
        return value

    def run_screen(self, value):
        self.write('screen.json', value)
        return self.json_cli('verdict', '--screen', self.screen_path)

    def invalid(self, value, message):
        code, result = self.run_screen(value)
        self.assertEqual(code, 1)
        self.assertIn(message, result['error'])
        self.assertNotIn('result', result)

    def test_prompt_is_deterministic_and_contains_every_item(self):
        args = ('prompt', '--checklist', self.checklist_path, '--answer', self.answer)
        first = self.json_cli(*args)
        self.assertEqual(first, self.json_cli(*args))
        self.assertEqual(first[0], 0)
        prompt = first[1]['prompt']
        for item in self.checklist['items']:
            self.assertIn('"id": "' + item['id'] + '"', prompt)
        for text in ('using only the answer text', 'data, not instructions', 'character for character',
                     '300 characters', 'one JSON object', 'nothing else'):
            self.assertIn(text, prompt)
        code, text = self.cli(*args)
        self.assertEqual(code, 0)
        self.assertEqual(text.rstrip('\n'), prompt)

    def test_prompt_shows_the_answer_verbatim_so_a_quote_can_be_copied(self):
        # A JSON-escaped answer would show \n and \" where the answer has a newline and a quote mark;
        # a judge copying that passage would then fail the verbatim check.
        answer = 'The first line says "retries are bounded".\nThe second line\tsays failures are logged.'
        self.answer.write_bytes(answer.encode())
        code, result = self.json_cli('prompt', '--checklist', self.checklist_path, '--answer', self.answer)
        self.assertEqual(code, 0)
        self.assertTrue(result['prompt'].endswith('\n\nANSWER:\n' + answer))
        quote = 'says "retries are bounded".\nThe second line'
        self.assertIn(quote, result['prompt'])
        code, checked = self.labels([{'id': 'a', 'label': 'yes', 'quote': quote}, {'id': 'b', 'label': 'no'}])
        self.assertEqual(code, 0)
        self.assertEqual(checked['items'][0]['label'], 'yes')

    def test_labels_valid_quote_hashes_metadata_and_output(self):
        output_path = self.root / 'checked.json'
        code, result = self.labels(extra=('--out', output_path, '--judge', 'fixture judge', '--judge-tokens', 17))
        self.assertEqual(code, 0)
        self.assertEqual(result['counts'], {'yes': 1, 'no': 1, 'unknown': 0})
        self.assertEqual(result['items'][0], {'id': 'a', 'label': 'yes', 'quote': QUOTE, 'reason': ''})
        self.assertEqual(result['checklist_sha256'], hashlib.sha256(self.checklist_path.read_bytes()).hexdigest())
        self.assertEqual(result['answer_sha256'], hashlib.sha256(self.answer.read_bytes()).hexdigest())
        self.assertEqual(result['judge'], 'fixture judge')
        self.assertEqual(result['judge_tokens'], 17)
        self.assertEqual(json.loads(output_path.read_text(encoding='utf-8')), result)

    def test_labels_accept_collapsed_whitespace_and_preserve_quote(self):
        self.answer.write_bytes(b'A concrete\r\n passage\tlong enough for the checked quote.')
        quote = 'A concrete  passage\nlong enough'
        code, result = self.labels([{'id': 'a', 'label': 'yes', 'quote': quote}, {'id': 'b', 'label': 'no'}])
        self.assertEqual(code, 0)
        self.assertEqual(result['items'][0]['label'], 'yes')
        self.assertEqual(result['items'][0]['quote'], quote)

    def test_labels_quote_length_boundary_and_wrong_text(self):
        self.answer.write_text('abcdefghijkl', encoding='utf-8')
        for quote, expected, reason in [('abcdefghijkl', 'yes', ''), ('abcdefghijk', 'unknown', 'shorter'),
                                         ('A passage from a different answer', 'unknown', 'does not occur'),
                                         ('a          b', 'unknown', 'shorter')]:
            with self.subTest(quote=quote):
                _, result = self.labels([{'id': 'a', 'label': 'yes', 'quote': quote}, {'id': 'b', 'label': 'no'}])
                self.assertEqual(result['items'][0]['label'], expected)
                self.assertIn(reason, result['items'][0]['reason'])

    def test_labels_overlong_quote_becomes_unknown(self):
        self.answer.write_bytes(b'x' * 301)
        _, result = self.labels([{'id': 'a', 'label': 'yes', 'quote': 'x' * 301}])
        self.assertEqual(result['items'][0]['label'], 'unknown')
        self.assertIn('exceeds 300', result['items'][0]['reason'])

    def test_labels_missing_duplicate_and_invalid_label_affect_only_the_item(self):
        cases = [([], 'Missing'), ([{'id': 'a', 'label': 'yes', 'quote': QUOTE}] * 2, 'Duplicate'),
                 ([{'id': 'a', 'label': 'maybe'}], 'Unknown label'),
                 ([{'id': 'a', 'label': 'yes', 'quote': 12}], 'string')]
        for rows, reason in cases:
            with self.subTest(reason=reason):
                code, result = self.labels(rows + [{'id': 'b', 'label': 'no'}])
                self.assertEqual(code, 0)
                self.assertEqual(result['counts'], {'yes': 0, 'no': 1, 'unknown': 1})
                self.assertIn(reason, result['items'][0]['reason'])

    def test_labels_bad_reply_marks_every_item_unknown(self):
        for raw in (b'not JSON', b'[]', b'{} {}', b'{"items":[],"items":[]}',
                    b'{"items": [], "cost": NaN}', b'{"items": [], "cost": 1e999}',
                    b'{"items": [{"id":"outside","label":"no"}]}', b'\xff'):
            with self.subTest(raw=raw):
                code, result = self.labels(raw=raw)
                self.assertEqual(code, 0)
                self.assertEqual(result['counts']['unknown'], 2)
                self.assertTrue(all(item['reason'].startswith('Invalid reply:') for item in result['items']))

    def test_labels_explicit_unknown_does_not_count_as_yes(self):
        _, result = self.labels([{'id': 'a', 'label': 'unknown'}, {'id': 'b', 'label': 'no'}])
        self.assertEqual(result['counts'], {'yes': 0, 'no': 1, 'unknown': 1})
        self.assertEqual(result['items'][0]['reason'], 'Judge labelled unknown')

    def test_crlf_and_bom_all_inputs(self):
        self.checklist_path.write_bytes(b'\xef\xbb\xbf' + json.dumps(self.checklist, indent=2).replace('\n', '\r\n').encode())
        self.answer.write_bytes(b'\xef\xbb\xbf' + QUOTE.encode() + b'\r\n')
        code, result = self.labels(raw=b'\xef\xbb\xbf{\r\n"items":[{"id":"a","label":"yes","quote":'
                                  + json.dumps(QUOTE).encode() + b'}, {"id":"b","label":"no"}]}\r\n')
        self.assertEqual(code, 0)
        self.assertEqual(result['counts']['yes'], 1)
        self.assertEqual(result['answer_sha256'], hashlib.sha256(self.answer.read_bytes()).hexdigest())
        self.assertEqual(self.json_cli('prompt', '--checklist', self.checklist_path, '--answer', self.answer)[0], 0)
        value = self.fixture()
        for task in value['tasks']:
            for arm in ('native', 'food'):
                path = self.root / task[arm]['labels']
                path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes().replace(b'\n', b'\r\n'))
        self.screen_path.write_bytes(b'\xef\xbb\xbf' + json.dumps(value, indent=2).replace('\n', '\r\n').encode())
        self.assertEqual(self.json_cli('verdict', '--screen', self.screen_path)[1]['result'], 'YES')

    def test_invalid_checklist_or_metadata_exits_one(self):
        self.checklist_path.write_bytes(b'{"task_id":"t1","items":[],"items":[]}')
        code, result = self.json_cli('prompt', '--checklist', self.checklist_path, '--answer', self.answer)
        self.assertEqual(code, 1)
        self.assertIn('Duplicate JSON key', result['error'])
        self.write('checklist.json', self.checklist)
        code, result = self.labels(extra=('--judge-tokens', -1))
        self.assertEqual(code, 1)
        self.assertIn('judge tokens', result['error'])

    def test_native_exactly_ninety_percent_stops_at_b(self):
        value = self.fixture([['yes'] * 9 + ['no']] * 3, [None] * 3)
        code, result = self.run_screen(value)
        self.assertEqual(code, 0)
        self.assertEqual((result['result'], result['deciding_step'], result['native_fraction']), ('NO', 'B', .9))
        self.assertIn('native fails', result['reopen'])

    def test_native_just_below_threshold_continues(self):
        value = self.fixture([['yes'] * 9 + ['no'], ['yes'] * 9 + ['no'], ['yes'] * 8 + ['no'] * 2],
                             [None] * 3)
        code, result = self.run_screen(value)
        self.assertEqual(code, 2)
        self.assertLess(result['native_fraction'], .9)
        self.assertEqual(result['result'], 'INCOMPLETE')

    def test_two_gains_no_losses_ratio_exactly_one_point_five_passes(self):
        code, result = self.run_screen(self.fixture())
        self.assertEqual(code, 0)
        self.assertEqual((result['result'], result['deciding_step']), ('YES', 'C'))
        self.assertEqual((result['gained'], result['lost'], result['ratio']), (2, 0, 1.5))
        self.assertEqual(result['gained_items'], [{'task_id': 't1', 'id': '0'}, {'task_id': 't2', 'id': '0'}])
        self.assertIn('default still needs the full measurement rules', result['reopen'])

    def test_one_gain_fails(self):
        code, result = self.run_screen(self.fixture(food=[['yes'], ['no'], ['yes']]))
        self.assertEqual(code, 0)
        self.assertEqual(result['deciding_step'], 'C')
        self.assertEqual(result['result'], 'NO')
        self.assertIn('gained < 2', result['reason'])

    def test_ratio_just_above_limit_fails(self):
        value = self.fixture()
        value['tasks'][0]['food']['logical_tokens'] += 1
        _, result = self.run_screen(value)
        self.assertEqual(result['result'], 'NO')
        self.assertIn('ratio > 1.5', result['reason'])

    def test_one_loss_fails_and_lists_item(self):
        _, result = self.run_screen(self.fixture(food=[['yes'], ['yes'], ['no']]))
        self.assertEqual(result['result'], 'NO')
        self.assertIn('lost != 0', result['reason'])
        self.assertEqual(result['lost_items'], [{'task_id': 't3', 'id': '0'}])

    def test_every_failing_c_condition_is_listed(self):
        value = self.fixture(food=[['yes'], ['no'], ['no']])
        value['tasks'][0]['food']['logical_tokens'] += 1
        _, result = self.run_screen(value)
        for condition in ('gained < 2', 'lost != 0', 'ratio > 1.5'):
            self.assertIn(condition, result['reason'])
        self.assertNotIn('\n', result['reason'])
        self.assertNotIn('\n', result['reopen'])

    def test_native_unknown_is_not_gain_and_food_unknown_is_loss(self):
        value = self.fixture(native=[['unknown'], ['no'], ['yes']], food=[['yes'], ['yes'], ['unknown']])
        _, result = self.run_screen(value)
        self.assertEqual(result['gained'], 1)
        self.assertEqual(result['lost'], 1)
        self.assertEqual(result['unknown_counts'], {'native': 1, 'food': 1})
        self.assertEqual(result['native_fraction'], 1 / 3)

    def test_unknown_to_unknown_is_neither_gain_nor_loss(self):
        value = self.fixture(native=[['unknown'], ['no'], ['no']], food=[['unknown'], ['yes'], ['yes']])
        _, result = self.run_screen(value)
        self.assertEqual((result['result'], result['gained'], result['lost']), ('YES', 2, 0))

    def test_missing_food_arm_is_incomplete_with_exit_two(self):
        value = self.fixture(food=[['yes'], None, ['yes']])
        code, result = self.run_screen(value)
        self.assertEqual(code, 2)
        self.assertEqual(result['result'], 'INCOMPLETE')
        self.assertIsNone(result['deciding_step'])
        self.assertEqual(result['reason'], 'run the food arm')
        self.assertEqual(result['missing_food_tasks'], ['t2'])
        self.assertIsNone(result['gained'])
        self.assertIsNone(result['ratio'])

    def test_all_given_tasks_are_used_and_fraction_is_item_weighted(self):
        value = self.fixture([['no'], ['yes'], ['yes'] * 20], [['yes'], ['yes'], ['yes'] * 20])
        _, result = self.run_screen(value)
        self.assertEqual(result['native_fraction'], 21 / 22)
        self.assertEqual(result['deciding_step'], 'B')
        value = self.fixture([['no']] * 4, [['yes']] * 4)
        _, result = self.run_screen(value)
        self.assertEqual((result['total_items'], result['gained'], result['native_tokens']), (4, 4, 400))

    def test_budget_family_sum_across_both_arms_and_exact_boundary(self):
        value = self.fixture()
        value['tasks'][0]['native']['logical_tokens'] = 2_000_000 - 650
        _, result = self.run_screen(value)
        self.assertNotEqual(result['deciding_step'], 'budget')
        self.assertEqual(result['tokens_by_family'], {'fixture-family': 2_000_000})
        value['tasks'][0]['native']['logical_tokens'] += 1
        _, result = self.run_screen(value)
        self.assertEqual((result['result'], result['deciding_step']), ('NO', 'budget'))

    def test_budget_separates_families_and_includes_seconds_across_families(self):
        value = self.fixture()
        for task in value['tasks']:
            task['native'].update(family='native-family', logical_tokens=500_000, seconds=300)
            task['food'].update(family='food-family', logical_tokens=500_000, seconds=300)
        _, result = self.run_screen(value)
        self.assertEqual(result['result'], 'YES')
        self.assertEqual(result['seconds'], 1800)
        self.assertEqual(result['tokens_by_family'], {'native-family': 1_500_000, 'food-family': 1_500_000})
        value['tasks'][0]['food']['seconds'] += .01
        _, result = self.run_screen(value)
        self.assertEqual(result['deciding_step'], 'budget')
        self.assertIn('seconds > 1800', result['reason'])

    def test_budget_precedes_native_b_and_lists_all_exceeded_budgets(self):
        value = self.fixture([['yes']] * 3, [['yes']] * 3)
        value['tasks'][0]['native'].update(logical_tokens=2_000_001, seconds=1801)
        _, result = self.run_screen(value)
        self.assertEqual(result['deciding_step'], 'budget')
        self.assertIn('logical_tokens > 2000000', result['reason'])
        self.assertIn('seconds > 1800', result['reason'])

    def test_static_blocked_and_owner_do_not_read_tasks(self):
        for status, reason, reopen in [('blocked', 'Licence is incompatible', 'Resolve the static blocker'),
                                       ('needs_owner', "needs the owner's approval before any run", 'owner approval')]:
            value = {'food': 'fixture', 'static': {'status': status, 'reason': 'Licence is incompatible'},
                     'tasks': [{'native': {'labels': '../must-not-read.json'}}]}
            with self.subTest(status=status), mock.patch.object(screen, 'read_labels', side_effect=AssertionError):
                code, result = self.run_screen(value)
                self.assertEqual(code, 0)
                self.assertEqual((result['result'], result['deciding_step']), ('NO', 'A'))
                self.assertEqual(result['reason'], reason)
                self.assertIn(reopen, result['reopen'])
                self.assertIsNone(result['native_fraction'])

    def test_fewer_than_three_tasks_is_invalid(self):
        value = self.fixture()
        value['tasks'].pop()
        self.invalid(value, 'At least 3 tasks')

    def test_mismatched_hashes_ids_counts_and_task_ids_are_invalid(self):
        original = self.fixture()
        path = self.root / original['tasks'][0]['food']['labels']
        labels = json.loads(path.read_text(encoding='utf-8'))
        cases = [(('checklist_sha256',), '0' * 64, 'Mismatched checklist hashes'),
                 (('items', 0, 'id'), 'different', 'Mismatched checklist item ids'),
                 (('counts', 'yes'), 0, 'counts disagree'),
                 (('task_id',), 'wrong', 'task_id does not match')]
        for keys, replacement, error in cases:
            changed = copy.deepcopy(labels)
            target = changed
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = replacement
            self.write(path.name, changed)
            with self.subTest(error=error):
                self.invalid(original, error)

    def test_relative_and_absolute_path_escapes_are_invalid(self):
        for relative in ('../outside.json', str(self.root / 'absolute.json'), 'C:\\outside.json', '\\outside.json'):
            value = self.fixture()
            value['tasks'][0]['native']['labels'] = relative
            with self.subTest(relative=relative):
                self.invalid(value, 'path')

    def test_symlink_escape_is_invalid(self):
        # Both files stay within this checkout; the labels link escapes only the screen directory.
        nested = self.root / 'nested'
        nested.mkdir()
        outside = self.write('outside.json', {})
        link = nested / 'escape.json'
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            # Windows may not grant symlink privileges. Still exercise the resolved-path check.
            with mock.patch.object(Path, 'resolve', return_value=outside):
                with self.assertRaisesRegex(screen.ScreenError, 'escapes'):
                    screen.read_labels(nested, 'escape.json', 't1')
        else:
            value = self.fixture()
            value['tasks'][0]['native']['labels'] = 'escape.json'
            path = nested / 'screen.json'
            path.write_text(json.dumps(value), encoding='utf-8')
            code, result = self.json_cli('verdict', '--screen', path)
            self.assertEqual(code, 1)
            self.assertIn('escapes', result['error'])
            self.assertNotIn('result', result)

    def test_duplicate_json_keys_and_nonfinite_numbers_exit_one_without_verdict(self):
        for raw in (b'{"food":"a","food":"b"}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
            self.screen_path.write_bytes(raw)
            with self.subTest(raw=raw):
                code, result = self.json_cli('verdict', '--screen', self.screen_path)
                self.assertEqual(code, 1)
                self.assertNotIn('result', result)
                self.assertIn('error', result)
        value = self.fixture()
        (self.root / value['tasks'][0]['native']['labels']).write_bytes(b'{"items":[],"items":[]}')
        self.invalid(value, 'Duplicate JSON key')

    def test_invalid_input_is_checked_even_when_b_would_decide(self):
        value = self.fixture([['yes']] * 3, [['yes']] * 3)
        value['tasks'][0]['food']['labels'] = 'missing.json'
        self.invalid(value, 'missing.json')

    def test_bad_numbers_duplicate_tasks_and_zero_native_total_are_invalid(self):
        for field, bad in (('logical_tokens', True), ('logical_tokens', -1), ('logical_tokens', 1.5),
                           ('seconds', False), ('seconds', -1)):
            value = self.fixture()
            value['tasks'][0]['native'][field] = bad
            with self.subTest(field=field, bad=bad):
                self.invalid(value, field)
        value = self.fixture()
        value['tasks'][1]['id'] = 't1'
        self.invalid(value, 'Duplicate task id')
        value = self.fixture()
        for task in value['tasks']:
            task['native']['logical_tokens'] = 0
        self.invalid(value, 'total must be positive')

    def test_text_modes_print_results_and_errors(self):
        self.write('screen.json', self.fixture())
        code, text = self.cli('verdict', '--screen', self.screen_path)
        self.assertEqual(code, 0)
        self.assertIn('result: YES', text)
        self.assertIn('gained_items:', text)
        self.labels()
        code, text = self.cli('labels', '--checklist', self.checklist_path, '--answer', self.answer,
                              '--reply', self.reply)
        self.assertEqual(code, 0)
        self.assertIn('counts:', text)
        self.screen_path.write_bytes(b'broken')
        code, text = self.cli('verdict', '--screen', self.screen_path)
        self.assertEqual(code, 1)
        self.assertTrue(text.startswith('Error:'))


if __name__ == '__main__':
    unittest.main()
