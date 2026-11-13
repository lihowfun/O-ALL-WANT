"""Writable host-workspace regressions. Synthetic executors only, no inference."""
from contextlib import ExitStack, redirect_stdout
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_packet
import cal_run as R
from cal_common import load, rows, save


class IntegrityTests(unittest.TestCase):
    def test_placeholder_names_match_retained_cli_builder_evidence(self):
        evidence = load(R.HERE / 'fixtures/host-preflight/codex-0.167.2-protected-paths.json')
        self.assertEqual(set(evidence['protected_names']), R.SANDBOX_PLACEHOLDERS)
        binary_excerpt = bytes.fromhex(evidence['builder_bytes_hex'])
        for literal in (b'.git', b'.age', b'ents', b'.cod', b'ex', b'.aws'):
            self.assertIn(literal, binary_excerpt)

    def workspace(self, root):
        work = root / 'workspace'
        (work / 'review_out').mkdir(parents=True)
        (work / 'source.py').write_text('original')
        return work, R.snapshot(work)

    def test_only_exact_empty_top_level_cli_directories_are_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            work, before = self.workspace(Path(td))
            for name in R.SANDBOX_PLACEHOLDERS:
                (work / name).mkdir()
            result = R.workspace_integrity(work, before, True)
            self.assertTrue(result['isolation_complete'])
            self.assertEqual([p['path'] for p in result['sandbox_placeholders']], sorted(R.SANDBOX_PLACEHOLDERS))
            # Grader policy has no placeholder exception.
            self.assertFalse(R.workspace_unchanged(work, before))
            (work / '.git' / 'unexpected').mkdir()
            result = R.workspace_integrity(work, before, True)
            self.assertFalse(result['isolation_complete'])
            self.assertEqual(result['source_changed_paths'], ['.git', '.git/unexpected'])
            self.assertNotIn('.git', [p['path'] for p in result['sandbox_placeholders']])

    def test_empty_files_links_and_unrecognized_directories_are_violations(self):
        for kind in ('file', 'symlink', 'other-directory', 'nested-placeholder', 'special'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                work, before = self.workspace(Path(td))
                if kind == 'file': (work / '.git').touch()
                if kind == 'symlink': (work / '.codex').symlink_to(work / 'review_out', target_is_directory=True)
                if kind == 'other-directory': (work / '.oaw').mkdir()
                if kind == 'nested-placeholder': (work / 'new' / '.aws').mkdir(parents=True)
                if kind == 'special': os.mkfifo(work / '.aws')
                result = R.workspace_integrity(work, before, True)
                self.assertFalse(result['isolation_complete'])
                self.assertEqual(result['sandbox_placeholders'], [])

    def test_existing_protected_packet_entries_cannot_be_exempted(self):
        with tempfile.TemporaryDirectory() as td:
            work, _ = self.workspace(Path(td))
            (work / '.agents').mkdir()
            source = work / '.agents' / 'instruction.md'
            source.write_text('original instruction')
            before = R.snapshot(work)
            source.unlink()
            result = R.workspace_integrity(work, before, True)
            self.assertFalse(result['isolation_complete'])
            self.assertEqual(result['source_changed_paths'], ['.agents/instruction.md'])
            self.assertEqual(result['sandbox_placeholders'], [])

    def test_output_link_and_removed_original_directory_are_detected(self):
        with tempfile.TemporaryDirectory() as td:
            work, _ = self.workspace(Path(td))
            (work / 'original-directory').mkdir()
            before = R.snapshot(work)
            (work / 'original-directory').rmdir()
            (work / 'review_out' / 'escape').symlink_to('/does-not-exist')
            result = R.workspace_integrity(work, before, True)
            self.assertEqual(result['source_changed_paths'], ['original-directory', 'review_out/escape'])


class NativeRecordingTests(unittest.TestCase):
    def test_native_mutations_are_recorded_terminal_with_paths_and_digests(self):
        for mutation, changed in (('overwrite', ['source.py']), ('remove', ['source.py']),
                                  ('add-file', ['added.txt']), ('add-directory', ['unapproved']),
                                  ('placeholders-only', [])):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as td, ExitStack() as stack:
                root = Path(td)
                packet = root / 'packet'; packet.mkdir()
                (packet / 'source.py').write_text('original')
                manifest = build_packet.inventory(packet)
                state = root / 'state'; state.mkdir()
                actual_load = R.load
                stack.enter_context(patch.dict(os.environ, {}, clear=True))
                stack.enter_context(patch.object(R, 'load', side_effect=lambda p: manifest if Path(p) == R.HERE / 'packet_manifest.json' else actual_load(p)))
                stack.enter_context(patch.object(R, 'frozen', return_value='a' * 64))
                stack.enter_context(patch.object(R, 'check_out', return_value=state))
                stack.enter_context(patch.object(R, 'gate_check', return_value={'key_sha256': 'b' * 64, 'cells': {'codex': {'inflight_allowance': 1000000}}}))
                stack.enter_context(patch.object(R.cal_launch, 'available'))
                stack.enter_context(patch.object(R, 'auth_home', return_value='subscription_chatgpt'))
                stack.enter_context(patch.object(R, 'cli_identity', return_value=R.CELLS['codex'][1]))
                def execute(cell, cli, work, home, parent, *args):
                    for name in R.SANDBOX_PLACEHOLDERS: (work / name).mkdir()
                    if mutation == 'overwrite': (work / 'source.py').write_text('changed')
                    if mutation == 'remove': (work / 'source.py').unlink()
                    if mutation == 'add-file': (work / 'added.txt').write_text('added')
                    if mutation == 'add-directory': (work / 'unapproved').mkdir()
                    save(work / 'review_out/report.json', {'completed': True, 'findings': [], 'uncertainties': []})
                    (parent / 'events.jsonl').write_bytes(b'')
                    return {'tokens_total': 100, 'tokens_noncache': 100, 'seconds': 1,
                            'metering_complete': True, 'result_seen': True, 'exit': 0,
                            'models_seen': [R.CELLS['codex'][0]]}
                launch = stack.enter_context(patch.object(R, 'execute', side_effect=execute))
                args = ['native', '--cell', 'codex', '--only', 'N1', '--packet', str(packet),
                        '--out', str(state), '--cli', str(root / 'never-executed'),
                        '--auth-file', str(root / 'never-read'), '--gate', str(root / 'unused-gate')]
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(R.main(args), 5 if changed else 0)
                    self.assertEqual(R.main(args), 0)  # Recorded, never redrawn.
                self.assertEqual(launch.call_count, 1)
                recorded = rows(state / 'rows-codex.jsonl')
                self.assertEqual(len(recorded), 1)
                row = recorded[0]
                self.assertEqual(row['status'], 'isolation incomplete' if changed else 'completed')
                self.assertEqual(row['source_changed_paths'], changed)
                self.assertEqual(row['sources_changed'], bool(changed))
                self.assertEqual(row['packet_sha256_before'], manifest['tree_sha256'])
                self.assertEqual(row['packet_sha256_after'] == manifest['tree_sha256'], mutation in ('add-directory', 'placeholders-only'))
                self.assertEqual(len(row['sandbox_placeholders']), 4)
                self.assertFalse(row['retryable'])
                if changed:
                    self.assertIn('isolation incomplete', output.getvalue())
                    self.assertIn(changed[0], output.getvalue())
                self.assertEqual((packet / 'source.py').read_text(), 'original')
