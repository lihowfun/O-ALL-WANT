# Design notes: questions-new.json (n1-n9)

Repo: frappe/erpnext @ d9cb9169dcc144cba46f7ddfcf90b0ab7b1e6aa9. Facts come from reading the source with
rg/sed and a small python-ast helper that finds the function enclosing a given line. No indexing or
code-graph tool was used. The usual scope is "production code": `*.po`/`*.pot` translation files excluded,
tests (`test_*`, `tests/`) and `erpnext/patches/` excluded. JS, JSON and hooks.py were searched too.

Topics avoided: update_bin_qty / Bin qty, get_valuation_rate raise_error_if_no_rate, deferred accounting job,
cost_center in get_item_details.

| id | type | why chosen | how verified / completeness |
|----|------|-----------|-----------------------------|
| n1 | impact (multi-hop) | Credit-limit enforcement is a cross-module rule (selling, stock, accounts). Maintainers often ask "where is this enforced?". | `rg -n "check_credit_limit\("` over the whole repo: 21 hits, 1 test file, 0 patches. Every direct call is in one of 5 functions. The `doc.check_credit_limit()` / `self.check_credit_limit()` method calls were followed one hop up (on_submit, on_update_after_submit, StatusService.update_status, ChildItemUpdater._post_update) and then to entry points (`rg "update_status\("`, `close_or_unclose_sales_orders`, `item_close.REOPEN_STATUS`, `update_child_qty_rate` in public/js/utils.js). Subclasses checked with `rg "class \w+\((SalesInvoice|DeliveryNote|SalesOrder|JournalEntry)\)"`: only POSInvoice. No override_doctype_class in hooks.py. |
| n2 | impact | A realistic "change the return type" question on a helper shared by buying and stock. Some callers survive and some do not. | `rg -n "get_last_purchase_details\b"`: 5 call sites, none in tests or patches. Each site was read for truthiness guards vs `.update()`/`.get()`. Upstream reach: `rg "update_last_purchase_rate|item_last_purchase_rate|get_last_purchase_rate"` and `rg "get_price_list_rate\("`. |
| n3 | impact | Variant to template BOM fallback is a common change request. The answer mixes Python callers, a JS frappe.call, and lookalike code that does not use the function. | `rg -n "get_default_bom"` over py/js/json/html: 7 Python call sites + 1 JS frappe.call. `rg "buying\.get_default_bom\|get_default_bom\("` in JS shows the JS helper is never invoked. The Work Order mapper (`_default_bom_for_item`, `_variant_default_bom`) was read to confirm it does not call get_default_bom. |
| n4 | impact | Budget checks: a maintainer wants to know which postings run the legacy per-entry check and how the legacy setting changes that. | `rg -n "validate_expense_against_budget"`: 3 call sites (plus 1 comment in projects/costing/budgets.py), none in tests or patches. `rg "use_legacy_budget_controller"` and `rg "validate_budget\("` give the gating and the upstream callers. `rg "process_gl_map\("` shows the other routes into distribute_gl_based_on_cost_center_allocation. |
| n5 | flow | Daily scheduler job → doc submit → background job → per-subscription state machine across 3 files. | hooks.py daily_maintenance entry → process_subscription.py → subscription.py (process, can_generate_new_invoice, create_invoice helpers, set_subscription_status). Read end to end. |
| n6 | flow | Stock reposting is central and often debugged; the hourly job has early exits, ordering and error recovery. | hooks.py hourly_maintenance + cron 0/15 → repost_item_valuation.py functions; imports followed to stock_ledger.repost_future_sle, accounts.utils.repost_gle_for_stock_vouchers, stock_closing_entry.mark_closing_entries_outdated, project.update_consumed_material_cost_for_vouchers. |
| n7 | flow | Form button → whitelisted method → submitted log → level-wise background jobs advanced by a cron. Manufacturing module. | bom_update_tool.js handler → bom_update_tool.py → bom_update_log.py → bom_updation_utils.py; hooks.py cron "0/15 * * * *" checked for resume_bom_cost_update_jobs. |
| n8 | mechanism | Exchange-rate precedence (stored, reverse, pegged, API, fallbacks) is a common source of confusion. | Read get_exchange_rate, get_stored_exchange_rate, get_pegged_rate, get_pegged_currencies, format_ces_api and currency_exchange_settings.get_auth_params. |
| n9 | mechanism | How SLA selection works: hooks wildcard entry point, filters, entity specificity, defaults, keeping the current SLA. | hooks.py doc_events["*"]["validate"] → service_level_agreement.apply and its helpers, read in full. |

Every `where` was checked by build/check_where.py, which uses ast for Python (Class.method and module-level
assignments such as `scheduler_events`) and definition regexes for JS. Result: 176 locations, 0 problems.
A negative test with fake symbols was correctly rejected.

## Known ambiguities

- n1: The hypothetical "on hold" throw could be placed before or after the `if not credit_limit: return` guard.
  This changes when it fires but not which callers or paths reach the function. Update Items reaches
  SalesOrder.check_credit_limit twice: explicitly in `_post_update`, then again through `parent.save()` →
  on_update_after_submit. Either description is acceptable.
- n2: The routes into get_price_list_rate are given as examples ("e.g."). There are more, such as the SO→PO mapper,
  packed_item, and pricing_rule through `frappe.get_attr`. An answer that names extra routes should not be
  penalised.
- n4: The fact that the GL-level legacy call also runs when the new budget controller is on describes the code
  as it is. Whether that is intended is not settled; projects/costing/budgets.py has a comment suggesting it is.
- n5: `posting_date` comes from `getdate(None)` (today); this reads frappe's getdate semantics.
- n7: The resume_bom_cost_update_jobs docstring says "every 5 minutes", but hooks.py schedules it every 15
  minutes. The reference follows hooks.py.
- n9: The question uses Issue as an example, but the mechanism is generic for any doctype that has an SLA.
