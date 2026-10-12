"""Release gates exercised only with fabricated files in temporary directories.

No real dataset is read, final evaluation authorized, review installed or release
archive created. ZIP tests serialize tiny synthetic fixtures in memory only.
"""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import package_tactical_release as release


class TacticalReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        original = {"README.md": b"Frozen original readme\n", "sportslab/core.py": b"# original fixture\n",
                    release.NFL_SNAPSHOT: b"synthetic NFL snapshot fixture; not source data"}
        files = [dict(path=p, bytes=len(b), sha256=release.digest(b)) for p, b in sorted(original.items())]
        manifest = release.canonical(dict(schema_version=1, file_count=len(files), files=files))
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as z:
            for path, raw in original.items():
                z.writestr(release.PREFIX + path, raw)
            z.writestr(release.PREFIX + "PUBLISH_MANIFEST.json", manifest)
        self.put(release.ARCHIVE, archive.getvalue())
        self.put(release.BASE_MANIFEST, manifest)
        self.put(release.BASE_HASHES, b'{"synthetic":"fixture"}\n')
        anchors = {p: release.digest((self.root / p).read_bytes()) for p in release.PRESERVED_SHA256}
        self.anchor_patch = patch.object(release, "PRESERVED_SHA256", anchors)
        self.anchor_patch.start(); self.addCleanup(self.anchor_patch.stop)
        self.spec = [self.spec_item("experiments/tactical/example.py", "code", "original_code", True)]
        self.put(self.spec[0]["path"], b"# fabricated source fixture\n")
        for task in release.TASKS:
            name = f"reports/tactical/release_status/{task}.json"
            self.spec.append(self.spec_item(name, "terminal_status", "original_research"))
            self.put_json(name, dict(schema_version=1, task=task, status="terminal_blocked", terminal=True,
                                     reason_code="source_integrity_failure"))
        self.spec_patch = patch.object(release, "candidate_spec", side_effect=lambda: copy.deepcopy(self.spec))
        self.spec_patch.start(); self.addCleanup(self.spec_patch.stop)
        self.refresh()

    @staticmethod
    def spec_item(path, kind, source, required=False):
        return dict(path=path, kind=kind, sources=[source], required=required, risk="fixture_only")

    def put(self, name, raw):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)

    def put_json(self, name, value):
        self.put(name, release.canonical(value))

    def refresh(self):
        self.document, self.payloads = release.inventory(self.root)
        self.review = dict(schema_version=1, review_type="independent_final_tactical_source_release_review", status="cleared",
            reviewer="SYNTHETIC TEST FIXTURE ONLY", independent=True, inventory_sha256=release.digest(release.canonical(self.document)),
            intended_use="independent_noncommercial_research",
            decisions={r["path"]: "include" for r in self.document["candidates"]},
            files={r["path"]: dict(bytes=r["bytes"], sha256=r["sha256"]) for r in self.document["candidates"]},
            content_checks={k: True for k in release.CONTENT_CHECKS}, source_scopes={}, studies={})
        sources = {s for r in self.document["candidates"] for s in r["sources"] if s != "preserved_four_sport"}
        for source in sources:
            self.review["source_scopes"][source] = dict(paths=sorted(r["path"] for r in self.document["candidates"] if source in r["sources"]),
                checks={key: True for key in release.SOURCE_RULES[source]["checks"]})
        for task in release.TASKS:
            name = f"reports/tactical/release_status/{task}.json"
            self.review["studies"][task] = dict(state="terminal_blocked", evidence_path=name,
                evidence_sha256=release.digest((self.root / name).read_bytes()),
                checks=dict(independently_audited=True, honest_status=True, privacy_reviewed=True))

    def validate(self):
        raw = release.canonical(self.review)
        return release.validate_review(self.root, self.document, self.payloads, raw, release.digest(raw))

    def test_preserved_archive_bytes_supply_original_and_manifest(self):
        self.put("README.md", b"Workspace file deliberately different")
        doc, payload = release.inventory(self.root)
        self.assertEqual(payload["README.md"], b"Frozen original readme\n")
        self.assertIn("PUBLISH_MANIFEST.json", payload)
        self.assertEqual(doc["preserved_sha256"], release.PRESERVED_SHA256)
        self.assertEqual((self.root / "README.md").read_bytes(), b"Workspace file deliberately different")

    def test_altered_trust_anchor_rejected(self):
        self.put(release.BASE_MANIFEST, b"changed")
        with self.assertRaisesRegex(ValueError, "trust anchor"):
            release.inventory(self.root)

    def test_draft_has_no_zip_or_approval(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(release.main(["--root", str(self.root)]), 0)
        self.assertFalse((self.root / "artifacts/tactical/release").exists())
        self.assertEqual(json.loads((self.root / release.DRAFT_DIR / "inventory.json").read_text())["status"], "draft_not_approved")
        for name, raw in before.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def test_cli_final_requires_external_review_and_hash(self):
        for args in (["--write-zip"], ["--review", "review.json"], ["--review-sha256", "0" * 64]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                release.main(["--root", str(self.root), *args])
        self.assertFalse((self.root / "artifacts/tactical/release").exists())

    def test_review_hash_exact(self):
        with self.assertRaisesRegex(ValueError, "review hash"):
            release.validate_review(self.root, self.document, self.payloads, release.canonical(self.review), "0" * 64)

    def test_no_generic_source_review_or_self_approval(self):
        for key, value in [("review_type", "source_only"), ("independent", False), ("status", "pending"),
                           ("intended_use", "commercial"), ("reviewer", "")]:
            old = self.review[key]; self.review[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.validate()
            self.review[key] = old

    def test_file_content_and_inventory_are_exactly_bound(self):
        name = "experiments/tactical/example.py"
        self.put(name, b"changed after review")
        self.document, self.payloads = release.inventory(self.root)
        with self.assertRaisesRegex(ValueError, "inventory changed"): self.validate()

    def test_exact_file_set_and_hashes(self):
        for change in ("extra", "missing", "sha", "size"):
            prior = copy.deepcopy(self.review)
            if change == "extra": self.review["files"]["data/raw.csv"] = dict(bytes=0, sha256="0" * 64)
            elif change == "missing": del self.review["files"]["README.md"]
            elif change == "sha": self.review["files"]["README.md"]["sha256"] = "0" * 64
            else: self.review["files"]["README.md"]["bytes"] += 1
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate()
            self.review = prior

    def test_every_candidate_needs_disposition(self):
        del self.review["decisions"]["README.md"]
        with self.assertRaises(ValueError): self.validate()

    def test_required_source_file_cannot_be_excluded(self):
        self.review["decisions"]["experiments/tactical/example.py"] = "exclude"
        with self.assertRaisesRegex(ValueError, "Required"): self.validate()

    def test_missing_selected_file_is_blocked(self):
        self.spec.append(self.spec_item("docs/tactical/missing.md", "documentation", "original_research", True))
        self.refresh()
        with self.assertRaisesRegex(ValueError, "missing"): self.validate()

    def test_optional_missing_file_may_only_be_explicitly_excluded(self):
        name = "docs/tactical/optional.md"
        self.spec.append(self.spec_item(name, "documentation", "original_research")); self.refresh()
        self.review["decisions"][name] = "exclude"; del self.review["files"][name]
        self.review["source_scopes"]["original_research"]["paths"].remove(name)
        self.validate()

    def test_seven_study_cohort_is_mandatory(self):
        del self.review["studies"]["tennis_execution"]
        with self.assertRaises(ValueError): self.validate()

    def test_pending_and_running_do_not_become_complete(self):
        for status in ("pending", "running", "development_complete", "failed"):
            self.review["studies"]["soccer"]["state"] = status
            with self.subTest(status=status), self.assertRaises(ValueError): self.validate()

    def test_reviewed_terminal_status_is_explicit(self):
        m = self.validate()
        self.assertEqual(set(m["studies"].values()), {"terminal_blocked"})
        self.assertNotIn("completed", json.dumps(m["studies"]))

    def test_terminal_status_cannot_smuggle_individual_rows(self):
        name = "reports/tactical/release_status/tennis_execution.json"
        status = json.loads((self.root / name).read_text()); status["players"] = ["private participant"]
        self.put_json(name, status); self.refresh()
        with self.assertRaises(ValueError): self.validate()

    def test_ordinary_pending_reason_not_terminal(self):
        name = "reports/tactical/release_status/baseball.json"
        status = json.loads((self.root / name).read_text()); status["reason_code"] = "still_running"
        self.put_json(name, status); self.refresh()
        with self.assertRaisesRegex(ValueError, "Pending"): self.validate()

    def test_changed_terminal_evidence_rejected(self):
        self.put_json("reports/tactical/release_status/soccer.json", {"status": "changed"})
        with self.assertRaisesRegex(ValueError, "Study evidence changed"): self.validate()

    def test_missing_independent_privacy_check_rejected(self):
        self.review["studies"]["tennis_execution"]["checks"]["privacy_reviewed"] = False
        with self.assertRaises(ValueError): self.validate()

    def test_completed_status_must_pass_actual_final_view_gate(self):
        task = "soccer"; view = f"reports/tactical/model_views/{task}.json"; blocked = f"reports/tactical/release_status/{task}.json"
        self.spec.append(self.spec_item(view, "sanitized_final_aggregate", "original_research"))
        self.put_json(view, {"synthetic_fixture_only": True}); self.put_json(release.VIEW_REVIEW, {"synthetic_fixture_only": True})
        self.refresh(); self.review["decisions"][blocked] = "exclude"; del self.review["files"][blocked]
        self.review["source_scopes"]["original_research"]["paths"].remove(blocked)
        self.review["studies"][task].update(state="completed_audited", evidence_path=release.VIEW_REVIEW,
            evidence_sha256=release.digest((self.root / release.VIEW_REVIEW).read_bytes()))
        with self.assertRaisesRegex(ValueError, "incomplete"): self.validate()
        with patch("experiments.tactical.model_views.load_verified_view", return_value=("verified_final_available", {})):
            with self.assertRaisesRegex(ValueError, "all seven completed"): self.validate()
            with patch.object(release, "verify_detached_snapshot"):
                self.assertEqual(self.validate()["studies"][task], "completed_audited")

    def test_privacy_and_licenses_are_not_overridden_by_code_license(self):
        name = "docs/tactical/byu_summary.md"
        self.spec.append(self.spec_item(name, "documentation", "byu")); self.put(name, b"Synthetic aggregate document")
        self.refresh()
        with self.assertRaisesRegex(ValueError, "notice"): self.validate()
        for notice in release.NOTICES["byu"]:
            self.spec.append(self.spec_item(notice, "license_notice", "byu")); self.put(notice, b"Synthetic license notice")
        self.refresh(); self.validate()
        self.review["source_scopes"]["byu"]["checks"]["all_eight_individual_results_suppressed"] = False
        with self.assertRaises(ValueError): self.validate()

    def test_source_scope_paths_are_exact(self):
        self.review["source_scopes"]["original_code"]["paths"].append("unapproved.py")
        with self.assertRaisesRegex(ValueError, "publication scope"): self.validate()

    def test_no_content_check_may_be_skipped(self):
        self.review["content_checks"]["no_unreviewed_small_cells"] = False
        with self.assertRaises(ValueError): self.validate()

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError): release.parse(b'{"status":"cleared","status":"pending"}')
        with self.assertRaises(ValueError): release.parse(b'{"x":NaN}')

    def test_forbidden_paths_even_if_added_to_candidate_catalog(self):
        for name in ("data/source.csv", "artifacts/tactical/model.json", "docs/file.pdf", "reports/cache.sqlite3", "scripts/private.pkl", "docs/.env"):
            item = self.spec_item(name, "documentation", "original_research")
            self.spec.append(item); self.put(name, b"synthetic fixture"); self.refresh()
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Forbidden"): self.validate()
            self.spec.remove(item)

    def test_parent_symlink_file_symlink_and_traversal_rejected(self):
        external = self.root / "external"; external.mkdir()
        (external / "item.md").write_text("fake")
        (self.root / "linked").symlink_to(external, target_is_directory=True)
        (self.root / "linked.md").symlink_to(external / "item.md")
        for name in ("../escape", "/absolute", "docs//double", "docs/../relative", "docs\\windows", "linked/item.md", "linked.md", "C:/file", "docs/file:stream", "docs/*.md"):
            with self.subTest(name=name), self.assertRaises(ValueError): release.path_for(self.root, name)

    def test_reproducible_zip_bytes_order_dates_modes_and_manifest(self):
        manifest = self.validate()
        first = release.reproducible_zip(self.payloads, manifest)
        self.assertEqual(first, release.reproducible_zip(dict(reversed(list(self.payloads.items()))), manifest))
        with zipfile.ZipFile(io.BytesIO(first)) as z:
            self.assertEqual(z.namelist(), sorted(z.namelist()))
            for info in z.infolist():
                self.assertEqual(info.date_time, release.FIXED_TIME)
                self.assertEqual((info.external_attr >> 16) & 0o777, 0o644)
            for record in manifest["files"]:
                self.assertEqual(release.digest(z.read(release.PREFIX + record["path"])), record["sha256"])
            self.assertEqual(json.loads(z.read(release.PREFIX + release.FINAL_MANIFEST)), manifest)
        self.assertFalse(list(self.root.rglob("*tactical-source.zip")))

    def test_payload_mutation_before_serialization_fails(self):
        manifest = self.validate(); self.payloads["README.md"] = b"tampered"
        with self.assertRaisesRegex(ValueError, "serialization"): release.reproducible_zip(self.payloads, manifest)

    def complete_synthetic_seven_studies(self, numerical_mutation=None):
        """Entirely fabricated evidence, exclusively under self.temp."""
        from experiments.tactical import model_views as v
        implementation = {}
        for name in v.IMPLEMENTATION:
            self.spec.append(self.spec_item(name, "code", "original_code"))
            self.put(name, b"SYNTHETIC IMPLEMENTATION FIXTURE ONLY")
            implementation[name] = release.digest((self.root / name).read_bytes())
        # Simulate the live-process implementation identity using only fabricated
        # source bytes. Semantic result/view validation below remains real.
        for target, value in (("LIVE_ROOT", self.root), ("RUNNING_CODE_SHA256", implementation)):
            fixture_patch = patch.object(v, target, value)
            fixture_patch.start(); self.addCleanup(fixture_patch.stop)
        self.put_json(release.RESULT_REVIEW, {"synthetic_test_only": True})
        audit_hash = release.digest((self.root / release.RESULT_REVIEW).read_bytes())
        tasks, completion = {}, {}
        for task in release.TASKS:
            body = dict(task=task, evaluation_cohort=list(release.TASKS), metadata={"artifact_id": "b" * 64}, synthetic_test_only=True)
            binding_hash = release.digest(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
            binding = {**body, "binding_sha256": binding_hash}
            binding_path = f"artifacts/tactical/{task}/run_binding.json"
            self.put_json(binding_path, binding)
            report = dict(phase="frozen_evaluation", synthetic_test_only=True)
            if task == "basketball": report.update(phase="evaluation_complete", new_model_selection=False)
            elif task == "tennis": report.update(stage="locked_2025_evaluation", as_of="20260122")
            elif task == "baseball": report.update(task=task, targets={"swing": {}, "contact_given_swing": {}})
            elif task in ("baseball_mechanics", "tennis_execution"): report.update(task=task, status="evaluation_complete", new_model_selection=False)
            report_path = v._final_path(task, binding); self.put_json(report_path, report)
            contract = v.CONTRACTS[task]
            cases, clusters = (571, 82) if task == "baseball_mechanics" else (548, 8) if task == "tennis_execution" else (200, 25)
            metric = "macro_MAE" if task == "baseball_mechanics" else "joint_NLL_equal_player" if task == "tennis_execution" else "log_loss"
            targets = [dict(id=target, cohort=next(iter(contract["cohorts"])), cases=cases, clusters=clusters, case_set_sha256="a" * 64,
                models=[dict(id=contract["models"][0], case_set_sha256="a" * 64,
                    metrics={metric: dict(value=.5, cases=cases, clusters=clusters, status="reported")})],
                comparisons=[], reliability=[]) for target in contract["targets"]]
            view_path = f"reports/tactical/model_views/{task}.json"
            self.spec.append(self.spec_item(view_path, "sanitized_final_aggregate", "original_research"))
            self.put_json(view_path, dict(schema_version=1, task=task, phase="independently_verified_final_aggregate", targets=targets))
            tasks[task] = dict(status="verified_final", binding_sha256=binding_hash,
                binding_file_sha256=release.digest((self.root / binding_path).read_bytes()),
                final_report_sha256=release.digest((self.root / report_path).read_bytes()),
                view_sha256=release.digest((self.root / view_path).read_bytes()), checks={key: True for key in v.CHECKS})
            completion[task] = dict(status="verified_final", binding_sha256=binding_hash,
                final_report_sha256=tasks[task]["final_report_sha256"], independent_result_review_sha256=audit_hash)
        selections = {}
        for task, entry in tasks.items():
            path = f"artifacts/tactical/{task}/SELECTION_FREEZE.json"
            self.put_json(path, {"task": task, "synthetic_test_only": True})
            selections[task] = dict(binding_sha256=entry["binding_sha256"], selection_path=path,
                selection_sha256=release.digest((self.root / path).read_bytes()))
        self.put_json(release.GLOBAL_FREEZE, dict(schema_version=1, tasks=selections))
        numerical = dict(schema_version=1, review_type="tactical_final_numerical_review", status="verified_final",
            reviewer="SYNTHETIC TEST ONLY", independent=True, evaluation_freeze_sha256=release.digest((self.root / release.GLOBAL_FREEZE).read_bytes()),
            tasks={task: dict(status="verified_final", binding_sha256=entry["binding_sha256"], selection_sha256=selections[task]["selection_sha256"],
                final_report_sha256=entry["final_report_sha256"], checks={key: True for key in release.NUMERICAL_CHECKS}) for task, entry in tasks.items()})
        if numerical_mutation:
            numerical_mutation(numerical)
        self.put_json(release.RESULT_REVIEW, numerical)
        for proof in completion.values():
            proof["independent_result_review_sha256"] = release.digest((self.root / release.RESULT_REVIEW).read_bytes())
        self.put_json(release.VIEW_REVIEW, dict(schema_version=1, review_type="independent_final_model_view_review", status="cleared",
            reviewer="SYNTHETIC TEST ONLY", independent=True, implementation_sha256=implementation, seven_task_completion=completion, tasks=tasks))
        self.put_json(release.SNAPSHOT_REVIEW, dict(schema_version=1, review_type="independent_aggregate_snapshot_review", status="cleared",
            reviewer="SYNTHETIC TEST ONLY", independent=True, distribution_scope="local_noncommercial_aggregate_snapshot",
            local_final_review_sha256=release.digest((self.root / release.VIEW_REVIEW).read_bytes()), implementation_sha256=implementation,
            seven_task_completion=completion, tasks={task: dict(status="verified_final", view_sha256=entry["view_sha256"],
                checks={key: True for key in v.CHECKS | {"sanitized_snapshot_verified", "aggregate_distribution_authorized"}}) for task, entry in tasks.items()}))
        self.spec.append(self.spec_item(release.SNAPSHOT_REVIEW, "public_provenance", "original_research"))
        self.refresh(); self.set_completed_decisions()

    def set_completed_decisions(self):
        for task in release.TASKS:
            blocked = f"reports/tactical/release_status/{task}.json"
            self.review["decisions"][blocked] = "exclude"; del self.review["files"][blocked]
            self.review["source_scopes"]["original_research"]["paths"].remove(blocked)
            self.review["studies"][task].update(state="completed_audited", evidence_path=release.VIEW_REVIEW,
                evidence_sha256=release.digest((self.root / release.VIEW_REVIEW).read_bytes()))

    def test_real_validators_accept_only_fabricated_complete_detached_fixture(self):
        self.complete_synthetic_seven_studies()
        manifest = self.validate()
        self.assertEqual(set(manifest["studies"].values()), {"completed_audited"})
        raw = release.reproducible_zip(self.payloads, manifest)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            self.assertNotIn(release.PREFIX + release.VIEW_REVIEW, names)
            self.assertNotIn(release.PREFIX + release.RESULT_REVIEW, names)
            self.assertFalse(any("run_binding" in name for name in names))
            self.assertIn(release.PREFIX + release.SNAPSHOT_REVIEW, names)

    def test_snapshot_cannot_attest_unrelated_hashes(self):
        self.complete_synthetic_seven_studies()
        value = json.loads((self.root / release.SNAPSHOT_REVIEW).read_text())
        value["seven_task_completion"]["soccer"]["binding_sha256"] = "f" * 64
        self.put_json(release.SNAPSHOT_REVIEW, value); self.refresh(); self.set_completed_decisions()
        with self.assertRaisesRegex(ValueError, "provenance"): self.validate()

    def test_private_implementation_cannot_hide_missing_distribution_dependency(self):
        self.complete_synthetic_seven_studies()
        name = "experiments/tactical/web/app.js"
        self.review["decisions"][name] = "exclude"; del self.review["files"][name]
        self.review["source_scopes"]["original_code"]["paths"].remove(name)
        with self.assertRaisesRegex(ValueError, "dependencies missing"): self.validate()

    def test_bad_detached_distribution_check_rejected_even_with_valid_local_results(self):
        self.complete_synthetic_seven_studies()
        value = json.loads((self.root / release.SNAPSHOT_REVIEW).read_text())
        value["tasks"]["tennis_execution"]["checks"]["sanitized_snapshot_verified"] = False
        self.put_json(release.SNAPSHOT_REVIEW, value); self.refresh(); self.set_completed_decisions()
        with self.assertRaisesRegex(ValueError, "Sanitized extraction"): self.validate()

    def test_changed_numerical_audit_closes_completed_release(self):
        self.complete_synthetic_seven_studies()
        self.put_json(release.RESULT_REVIEW, {"synthetic_test_only": "changed"})
        with self.assertRaisesRegex(ValueError, "incomplete"): self.validate()

    def test_numerical_review_semantics_cannot_be_replaced_by_matching_hashes(self):
        base_spec = copy.deepcopy(self.spec)
        mutations = [lambda x: x.clear(), lambda x: x.update(status="pending"),
            lambda x: x.update(review_type="source_only_review"), lambda x: x.update(independent=False),
            lambda x: x.update(reviewer=""), lambda x: x.update(evaluation_freeze_sha256="not a hash"),
            lambda x: x["tasks"].pop("tennis_execution"),
            lambda x: x["tasks"]["soccer"].update(status="development_complete"),
            lambda x: x["tasks"]["soccer"]["checks"].update(saved_prediction_metrics_recomputed=False),
            lambda x: x["tasks"]["soccer"].update(binding_sha256="f" * 64)]
        for index, mutation in enumerate(mutations):
            self.spec = copy.deepcopy(base_spec)
            self.complete_synthetic_seven_studies(numerical_mutation=mutation)
            # All hashes are generated AFTER the faulty content, not stale. The
            # schema/status/coverage mismatch must itself prevent final release.
            with self.subTest(index=index), self.assertRaises(ValueError): self.validate()

    def test_numerical_review_validator_ignores_narrative_as_authority(self):
        self.complete_synthetic_seven_studies()
        audit = json.loads((self.root / release.RESULT_REVIEW).read_text())
        snapshot = json.loads((self.root / release.SNAPSHOT_REVIEW).read_text())
        audit["limitations"] = ["SYNTHETIC TEST ONLY"]
        release.validate_numerical_review(release.canonical(audit), snapshot["seven_task_completion"])
        audit["tasks"]["soccer"]["checks"]["no_test_reselection"] = False
        audit["notes"] = "Pretend approval text cannot override a failed required check"
        with self.assertRaises(ValueError):
            release.validate_numerical_review(release.canonical(audit), snapshot["seven_task_completion"])

    def test_actual_freeze_and_selections_are_required_without_copying_private_files(self):
        base_spec = copy.deepcopy(self.spec)
        for name in (release.GLOBAL_FREEZE, "artifacts/tactical/baseball/SELECTION_FREEZE.json"):
            self.spec = copy.deepcopy(base_spec); self.complete_synthetic_seven_studies()
            self.put_json(name, {"synthetic_test_only": "changed private metadata"})
            with self.subTest(name=name), self.assertRaises(ValueError): self.validate()

    def test_numerical_freeze_validator_cross_matches_exact_cohort_and_authority(self):
        self.complete_synthetic_seven_studies()
        audit = json.loads((self.root / release.RESULT_REVIEW).read_text())
        freeze = json.loads((self.root / release.GLOBAL_FREEZE).read_text())
        for change in (lambda x: x["tasks"].pop("tennis"),
                       lambda x: x["tasks"]["soccer"].update(binding_sha256="f" * 64),
                       lambda x: x["tasks"]["soccer"].update(selection_path="data/fake.json"),
                       lambda x: x["tasks"]["soccer"].update(selection_sha256="f" * 64)):
            value = copy.deepcopy(freeze); change(value); self.put_json(release.GLOBAL_FREEZE, value)
            # Rebind the global digest to ensure this is a semantic cross-check.
            audit["evaluation_freeze_sha256"] = release.digest((self.root / release.GLOBAL_FREEZE).read_bytes())
            with self.assertRaises(ValueError): release.verify_numerical_freeze(self.root, audit)

    def install_synthetic_privacy_mapping(self):
        original = b"# fabricated source\nlabel = 'PRIVATE_SENTINEL'\n"
        replacement = "SYNTHETIC_PUBLIC_LABEL"
        start = original.index(b"PRIVATE_SENTINEL")
        public = original[:start] + replacement.encode() + original[start + len(b"PRIVATE_SENTINEL"):]
        mapping = dict(original_path="private/frozen_fixture.py", archive_path="experiments/tactical/example.py",
            staged_path=release.PRIVACY_STAGE + "/experiments/tactical/example.py",
            original_sha256=release.digest(original), public_sha256=release.digest(public),
            operation="synthetic_privacy_fixture_only", edits=[dict(start=start, end=start + len(b"PRIVATE_SENTINEL"), replacement=replacement)])
        self.put(mapping["original_path"], original)
        mapping_patch = patch.object(release, "PRIVACY_COPIES", (mapping,))
        mapping_patch.start(); self.addCleanup(mapping_patch.stop)
        return mapping, original, public

    def test_fixed_privacy_staging_is_idempotent_and_preserves_original(self):
        mapping, original, public = self.install_synthetic_privacy_mapping()
        first = release.stage_privacy_copies(self.root)
        second = release.stage_privacy_copies(self.root)
        self.assertEqual(first, second)
        self.assertEqual((self.root / mapping["original_path"]).read_bytes(), original)
        self.assertEqual((self.root / mapping["staged_path"]).read_bytes(), public)
        self.assertNotIn(b"PRIVATE_SENTINEL", (self.root / release.PRIVACY_PROVENANCE).read_bytes())
        self.assertEqual(first["status"], "privacy_copies_prepared_not_approved")
        doc, payloads = release.inventory(self.root)
        record = next(r for r in doc["candidates"] if r["path"] == mapping["archive_path"])
        self.assertEqual(record["origin"], "privacy_sanitized_copy")
        self.assertEqual(record["privacy_copy"]["original_sha256"], release.digest(original))
        self.assertEqual(record["privacy_copy"]["public_sha256"], release.digest(public))
        self.assertEqual(payloads[mapping["archive_path"]], public)
        self.assertNotIn(mapping["original_path"], payloads)
        self.assertNotIn(mapping["staged_path"], payloads)

    def test_missing_staged_copy_never_falls_back_to_workspace_original(self):
        mapping, _, _ = self.install_synthetic_privacy_mapping()
        doc, payloads = release.inventory(self.root)
        record = next(r for r in doc["candidates"] if r["path"] == mapping["archive_path"])
        self.assertFalse(record["exists"])
        self.assertNotIn(mapping["archive_path"], payloads)

    def test_changed_original_or_public_copy_fails_closed(self):
        mapping, original, public = self.install_synthetic_privacy_mapping()
        self.put(mapping["original_path"], original + b"changed")
        with self.assertRaisesRegex(ValueError, "Frozen"): release.stage_privacy_copies(self.root)
        self.assertFalse((self.root / mapping["staged_path"]).exists())
        self.put(mapping["original_path"], original)
        release.stage_privacy_copies(self.root)
        self.put(mapping["staged_path"], public + b"unreviewed")
        with self.assertRaises(ValueError): release.stage_privacy_copies(self.root)
        with self.assertRaises(ValueError): release.inventory(self.root)
        self.assertEqual((self.root / mapping["original_path"]).read_bytes(), original)

    def test_invalid_exact_span_and_public_hash_rejected(self):
        mapping, original, _ = self.install_synthetic_privacy_mapping()
        for mutate in (lambda x: x.update(public_sha256="0" * 64),
                       lambda x: x["edits"][0].update(start=-1),
                       lambda x: x["edits"][0].update(end=len(original) + 1),
                       lambda x: x["edits"].append(copy.deepcopy(x["edits"][0]))):
            changed = copy.deepcopy(mapping); mutate(changed)
            with self.assertRaises(ValueError): release._privacy_copy(original, changed)

    def test_bounded_reads_reject_hardlinks_symlinks_special_and_large_files(self):
        self.put("one.txt", b"fixture")
        os.link(self.root / "one.txt", self.root / "alias.txt")
        with self.assertRaises(ValueError): release.read_bytes(self.root, "one.txt")
        with self.assertRaises(ValueError): release.read_bytes(self.root, "alias.txt")
        (self.root / "alias.txt").unlink()
        (self.root / "linked.txt").symlink_to(self.root / "one.txt")
        with self.assertRaises((ValueError, OSError)): release.read_bytes(self.root, "linked.txt")
        with self.assertRaises(ValueError): release.read_bytes(self.root, "one.txt", limit=2)
        os.mkfifo(self.root / "fifo")
        with self.assertRaises(ValueError): release.read_bytes(self.root, "fifo")
        self.assertEqual(release.read_bytes(self.root, "one.txt"), b"fixture")

    def test_alias_cannot_redirect_fixed_staging(self):
        mapping, original, _ = self.install_synthetic_privacy_mapping()
        stage = self.root / mapping["staged_path"]; stage.parent.mkdir(parents=True)
        stage.symlink_to(self.root / mapping["original_path"])
        with self.assertRaises((ValueError, OSError)): release.stage_privacy_copies(self.root)
        self.assertEqual((self.root / mapping["original_path"]).read_bytes(), original)

    def test_privacy_staging_cannot_be_combined_with_final_actions(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            release.main(["--root", str(self.root), "--stage-public-copies", "--review", "review.json", "--review-sha256", "0" * 64])
        self.assertFalse((self.root / release.PRIVACY_STAGE).exists())

    def test_explicit_local_only_documents_cannot_be_approved_into_release(self):
        name = release.REQUIRED_EXCLUSIONS[0]
        self.spec.append(self.spec_item(name, "documentation", "original_research"))
        self.put(name, b"SYNTHETIC LOCAL ONLY DOCUMENT"); self.refresh()
        with self.assertRaisesRegex(ValueError, "local-only"): self.validate()

    def test_default_catalog_is_explicit_and_covers_web_csv_notices(self):
        self.spec_patch.stop()
        specs = release.candidate_spec(); names = {r["path"] for r in specs}
        self.assertEqual(len(specs), len(names))
        benchmark = next(record for record in specs if record["path"] == "docs/tactical/BENCHMARK_RESULTS.md")
        self.assertTrue(benchmark["required"])
        self.assertEqual(benchmark["kind"], "research_synthesis")
        self.assertEqual(benchmark["sources"], sorted({source for sources in release.STUDY_SOURCES.values() for source in sources}))
        self.assertTrue({"experiments/tactical/web/app.js", "experiments/tactical/web/style.css", "experiments/tactical/web/index.html", "docs/research/SOCCER_BASKETBALL_FACTOR_INVENTORY.csv", "docs/research/notices/SKILLCORNER_BASKETBALL_MIT.txt"}.issubset(names))
        self.assertFalse(any("*" in p or "?" in p or p.startswith(("data/", "artifacts/")) for p in names))
        self.assertFalse(any(p.startswith("reports/research_") for p in names))
        self.assertIn("docs/tactical/TENNIS_EXECUTION_PROTOCOL_PUBLIC.md", names)
        self.assertNotIn("docs/tactical/TENNIS_EXECUTION_PROTOCOL_DRAFT.md", names)
        self.assertIn(release.DERIVED_LICENSE_NOTICE, names)
        self.assertIn(release.PUBLIC_COPY_NOTE, names)
        self.assertTrue(all(next(r for r in specs if r["path"] == path).get("required_decision") == "exclude" for path in release.REQUIRED_EXCLUSIONS))
        self.assertNotIn("docs/research/baseball_football/openbiomechanics_schema_audit.json", names)


if __name__ == "__main__":
    unittest.main()
