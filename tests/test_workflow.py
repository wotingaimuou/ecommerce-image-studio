"""Exercise failure gates and evidence recording with small synthetic fixtures."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from src.config import Config
from src.planner import compile_brief
from src.tools import record_image, error_action
from src.utils import BriefError

ROOT = Path(__file__).resolve().parents[1]

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.cfg = Config()
        self.brief = json.loads((ROOT / "examples/concept-mug.json").read_text(encoding="utf-8"))
        self.image = self.base / "reference.png"
        Image.new("RGB", (64, 64), "white").save(self.image)

    def plan(self, brief=None):
        return compile_brief(brief or self.brief, self.base, self.cfg)

    def qa(self, **overrides):
        result = dict(reviewer="test", appearance="pass", text="not_applicable",
                      count="pass", scene="pass", people="pass", notes="Synthetic fixture validation only.")
        result.update(overrides)
        return result

    def test_plan_never_claims_generated(self):
        plan = self.plan()
        self.assertEqual(plan["status"], "planned")
        self.assertFalse(plan["platform_rules_verified"])

    def test_real_product_requires_product_reference(self):
        self.brief["concept"] = False
        with self.assertRaises(BriefError):
            self.plan()

    def test_unknown_fact_rejected(self):
        self.brief["assets"][0]["fact_ids"] = ["unprovided"]
        with self.assertRaises(BriefError):
            self.plan()

    def test_bundle_count_conflict_rejected(self):
        a = self.brief["assets"][0]
        a.update(mode="sku-bundle", quantity=3, copy=["5件套"], references=[
            {"path": "reference.png", "role": "product"},
            {"path": "reference.png", "role": "template"}])
        with self.assertRaises(BriefError):
            self.plan()

    def test_unverified_appearance_is_not_accepted(self):
        r = record_image(self.plan(), "mug-hero", self.image,
                         self.qa(appearance="unverified"), self.base / "review", self.cfg)
        self.assertEqual(r["status"], "needs_review")
        self.assertTrue((self.base / "review/mug-hero.receipt.json").is_file())

    def test_wrong_ratio_needs_review(self):
        Image.new("RGB", (120, 60), "white").save(self.image)
        r = record_image(self.plan(), "mug-hero", self.image,
                         self.qa(), self.base / "review", self.cfg)
        self.assertFalse(r["machine_checks"]["aspect"])
        self.assertEqual(r["status"], "needs_review")

    def test_transparency_requires_actual_alpha(self):
        a = self.brief["assets"][0]
        a.update(mode="retouch", transparent=True, references=[{"path": "reference.png", "role": "product"}])
        r = record_image(self.plan(), "mug-hero", self.image,
                         self.qa(), self.base / "review", self.cfg)
        self.assertFalse(r["machine_checks"]["transparency"])
        self.assertEqual(r["status"], "needs_review")

    def test_output_cannot_be_silently_overwritten(self):
        plan = self.plan()
        out = self.base / "review"
        first = record_image(plan, "mug-hero", self.image, self.qa(), out, self.cfg)
        self.assertEqual(first["status"], "accepted")
        with self.assertRaises(FileExistsError):
            record_image(plan, "mug-hero", self.image, self.qa(), out, self.cfg)

    def test_network_failure_does_not_blindly_retry(self):
        self.assertFalse(error_action("network", 0, self.cfg)["retry"])
        self.assertEqual(error_action("network", 0, self.cfg)["action"],
                         "inspect_existing_result_then_decide")

    def test_transient_retries_are_bounded(self):
        self.assertTrue(error_action("unavailable", 0, self.cfg)["retry"])
        self.assertFalse(error_action("unavailable", 2, self.cfg)["retry"])

if __name__ == "__main__":
    unittest.main()

