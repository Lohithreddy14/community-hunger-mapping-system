"""
Automated tests for the Community Hunger Mapping System.

Run from the project folder (virtual environment active):

    python -m unittest discover tests -v

Each test uses its own temporary database, so your real data is never touched.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db          # noqa: E402
import scoring     # noqa: E402
from app import create_app   # noqa: E402
from validation import validate_community   # noqa: E402


def valid_payload(**overrides):
    data = {
        "name": "Test Area",
        "latitude": "12.95",
        "longitude": "77.60",
        "population": "3000",
        "total_families": "700",
        "families_needing_assistance": "140",
        "avg_household_income": "20000",
        "food_accessibility": "Moderate",
        "nearby_centers": "1",
        "notes": "Created by an automated test",
    }
    data.update(overrides)
    return data


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.db")
        self.app = create_app({"DATABASE": self.db_path, "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()


class DatabaseAndPagesTests(AppTestCase):
    def test_database_created_with_sample_data(self):
        self.assertTrue(os.path.exists(self.db_path))
        communities = self.client.get("/api/communities").get_json()
        centers = self.client.get("/api/centers").get_json()
        self.assertEqual(len(communities), 10)
        self.assertEqual(len(centers), 5)
        self.assertTrue(all(c["is_sample"] for c in communities))
        self.assertTrue(all(k["is_sample"] for k in centers))

    def test_all_pages_load_and_contain_navigation(self):
        for path in ("/", "/map", "/add", "/communities", "/centers"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            html = response.get_data(as_text=True)
            for link in ('href="/"', 'href="/map"', 'href="/add"',
                         'href="/communities"', 'href="/centers"'):
                self.assertIn(link, html, f"{link} missing on {path}")

    def test_edit_page_and_missing_pages(self):
        self.assertEqual(self.client.get("/edit/1").status_code, 200)
        self.assertEqual(self.client.get("/edit/9999").status_code, 404)
        self.assertEqual(self.client.get("/no-such-page").status_code, 404)
        api_404 = self.client.get("/api/communities/9999")
        self.assertEqual(api_404.status_code, 404)
        self.assertIn("error", api_404.get_json())

    def test_static_files_are_served(self):
        for path in ("/static/css/style.css", "/static/js/common.js", "/static/js/map.js",
                     "/static/js/dashboard.js", "/static/js/add_community.js",
                     "/static/js/communities.js", "/static/js/centers.js"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            response.close()


class DashboardAndAnalysisTests(AppTestCase):
    def test_stats_are_calculated_from_database(self):
        stats = self.client.get("/api/stats").get_json()
        communities = self.client.get("/api/communities").get_json()
        self.assertEqual(stats["total_areas"], len(communities))
        self.assertEqual(stats["total_families_needing_assistance"],
                         sum(c["families_needing_assistance"] for c in communities))
        self.assertEqual(stats["total_centers"], 5)
        self.assertEqual(sum(stats["category_counts"].values()), stats["total_areas"])
        self.assertEqual(sum(stats["families_by_category"].values()),
                         stats["total_families_needing_assistance"])
        self.assertEqual(stats["category_counts"],
                         {"lower": 3, "moderate": 4, "higher": 3})

    def test_analysis_endpoint(self):
        data = self.client.get("/api/analysis").get_json()
        self.assertIn("method", data)
        self.assertEqual(len(data["results"]), 10)
        self.assertAlmostEqual(sum(i["weight"] for i in data["method"]["indicators"]), 1.0)

    def test_category_filter(self):
        higher = self.client.get("/api/communities?category=higher").get_json()
        self.assertEqual(len(higher), 3)
        self.assertTrue(all(c["category"] == "higher" for c in higher))
        self.assertEqual(self.client.get("/api/communities?category=purple").status_code, 400)


class CreateUpdateDeleteTests(AppTestCase):
    def test_add_record_updates_dashboard_and_map_data(self):
        before = self.client.get("/api/stats").get_json()

        response = self.client.post("/api/communities", json=valid_payload(
            name="Demo Hamlet", families_needing_assistance="400", total_families="800",
            food_accessibility="Poor", nearby_centers="0", avg_household_income="9000"))
        self.assertEqual(response.status_code, 201)
        created = response.get_json()
        self.assertFalse(created["is_sample"])
        self.assertEqual(created["category"], "higher")     # a clearly high-need area

        after = self.client.get("/api/stats").get_json()
        self.assertEqual(after["total_areas"], before["total_areas"] + 1)
        self.assertEqual(after["total_families_needing_assistance"],
                         before["total_families_needing_assistance"] + 400)
        self.assertEqual(after["category_counts"]["higher"],
                         before["category_counts"]["higher"] + 1)
        self.assertEqual(after["user_records"], 1)
        self.assertEqual(after["recent"][0]["name"], "Demo Hamlet")

        listing = self.client.get("/api/communities").get_json()
        self.assertIn("Demo Hamlet", [c["name"] for c in listing])
        one = self.client.get(f"/api/communities/{created['id']}").get_json()
        self.assertEqual(one["name"], "Demo Hamlet")

    def test_data_survives_restart(self):
        self.client.post("/api/communities", json=valid_payload(name="Persistent Area"))
        # Start a brand-new app on the same database file (simulates a restart).
        restarted = create_app({"DATABASE": self.db_path, "TESTING": True}).test_client()
        names = [c["name"] for c in restarted.get("/api/communities").get_json()]
        self.assertIn("Persistent Area", names)
        # Sample data must not be loaded a second time.
        self.assertEqual(len(names), 11)

    def test_deleted_sample_data_is_not_reloaded(self):
        first_id = self.client.get("/api/communities").get_json()[0]["id"]
        self.assertEqual(self.client.delete(f"/api/communities/{first_id}").status_code, 200)
        restarted = create_app({"DATABASE": self.db_path, "TESTING": True}).test_client()
        self.assertEqual(len(restarted.get("/api/communities").get_json()), 9)

    def test_update_record_recalculates_category(self):
        created = self.client.post("/api/communities", json=valid_payload(
            families_needing_assistance="30", total_families="700",
            food_accessibility="Good", nearby_centers="3",
            avg_household_income="60000")).get_json()
        self.assertEqual(created["category"], "lower")

        updated = self.client.put(f"/api/communities/{created['id']}", json=valid_payload(
            families_needing_assistance="350", total_families="700",
            food_accessibility="Poor", nearby_centers="0",
            avg_household_income="9000"))
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["category"], "higher")

        self.assertEqual(self.client.put("/api/communities/9999", json=valid_payload()).status_code, 404)

    def test_delete_record(self):
        created = self.client.post("/api/communities", json=valid_payload()).get_json()
        before = self.client.get("/api/stats").get_json()["total_areas"]
        self.assertEqual(self.client.delete(f"/api/communities/{created['id']}").status_code, 200)
        self.assertEqual(self.client.get("/api/stats").get_json()["total_areas"], before - 1)
        self.assertEqual(self.client.delete(f"/api/communities/{created['id']}").status_code, 404)


class ValidationTests(AppTestCase):
    def assert_rejected(self, field, **overrides):
        response = self.client.post("/api/communities", json=valid_payload(**overrides))
        self.assertEqual(response.status_code, 400, f"{overrides} should be rejected")
        self.assertIn(field, response.get_json()["errors"])
        return response.get_json()["errors"][field]

    def test_required_fields(self):
        for field in ("name", "latitude", "longitude", "population", "families_needing_assistance"):
            message = self.assert_rejected(field, **{field: ""})
            self.assertIn("required", message)

    def test_invalid_values_are_rejected_with_messages(self):
        self.assert_rejected("latitude", latitude="95")
        self.assert_rejected("longitude", longitude="-200")
        self.assert_rejected("latitude", latitude="north")
        self.assert_rejected("population", population="0")
        self.assert_rejected("population", population="12.5")
        self.assert_rejected("population", population="-5")
        self.assert_rejected("families_needing_assistance", families_needing_assistance="-1")
        self.assert_rejected("families_needing_assistance", families_needing_assistance="5000")
        self.assert_rejected("total_families", total_families="100")     # fewer than 140 needing
        self.assert_rejected("total_families", total_families="9000")    # more than population
        self.assert_rejected("avg_household_income", avg_household_income="-1")
        self.assert_rejected("nearby_centers", nearby_centers="2.5")
        self.assert_rejected("food_accessibility", food_accessibility="Excellent")
        self.assert_rejected("name", name="A")
        self.assert_rejected("notes", notes="x" * 501)

    def test_bad_request_bodies(self):
        no_json = self.client.post("/api/communities", data="not json",
                                   content_type="application/json")
        self.assertEqual(no_json.status_code, 400)
        not_object = self.client.post("/api/communities", json=[1, 2, 3])
        self.assertEqual(not_object.status_code, 400)

    def test_rejected_record_is_not_saved(self):
        before = self.client.get("/api/stats").get_json()["total_areas"]
        self.client.post("/api/communities", json=valid_payload(latitude="999"))
        self.assertEqual(self.client.get("/api/stats").get_json()["total_areas"], before)

    def test_numbers_may_be_json_numbers_and_optional_fields_blank(self):
        response = self.client.post("/api/communities", json={
            "name": "Minimal Area", "latitude": 12.9, "longitude": 77.5,
            "population": 1000, "families_needing_assistance": 50,
        })
        self.assertEqual(response.status_code, 201)
        record = response.get_json()
        self.assertIsNone(record["avg_household_income"])
        self.assertIsNone(record["food_accessibility"])
        self.assertIsNone(record["nearby_centers"])
        self.assertIsNone(record["total_families"])

    def test_html_in_name_is_stored_as_text(self):
        # Escaping happens in the browser (escapeHtml); the API just stores the text.
        record = self.client.post("/api/communities",
                                  json=valid_payload(name="<b>Bold</b> Area")).get_json()
        self.assertEqual(record["name"], "<b>Bold</b> Area")


class ScoringTests(unittest.TestCase):
    BASE = {
        "population": 4000, "total_families": 1000, "families_needing_assistance": 100,
        "avg_household_income": 25000, "food_accessibility": "Moderate", "nearby_centers": 1,
        "latitude": 12.9, "longitude": 77.6,
    }

    def analyse(self, **changes):
        record = dict(self.BASE)
        record.update(changes)
        return scoring.analyse_community(record, [])

    def test_worked_example_from_methodology(self):
        # need 10% -> 25 ; access Moderate -> 50 ; centers 1 -> 60 ; income 25000 -> 50
        # score = 0.45*25 + 0.25*50 + 0.20*60 + 0.10*50 = 11.25 + 12.5 + 12 + 5 = 40.75
        result = self.analyse()
        self.assertEqual(result["score"], 40.8)
        self.assertEqual(result["category"]["key"], "moderate")

    def test_lowest_and_highest_scores(self):
        low = self.analyse(families_needing_assistance=0, food_accessibility="Good",
                           nearby_centers=5, avg_household_income=80000)
        self.assertEqual(low["score"], 0.0)
        self.assertEqual(low["category"]["key"], "lower")
        high = self.analyse(families_needing_assistance=500, food_accessibility="Poor",
                            nearby_centers=0, avg_household_income=5000)
        self.assertEqual(high["score"], 100.0)
        self.assertEqual(high["category"]["key"], "higher")

    def test_category_boundaries(self):
        self.assertEqual(scoring.categorize(34.9)["key"], "lower")
        self.assertEqual(scoring.categorize(35.0)["key"], "moderate")
        self.assertEqual(scoring.categorize(64.9)["key"], "moderate")
        self.assertEqual(scoring.categorize(65.0)["key"], "higher")

    def test_missing_optional_values_are_skipped_not_invented(self):
        result = self.analyse(avg_household_income=None, food_accessibility=None,
                              nearby_centers=None)
        self.assertEqual(result["indicators_used"], 1)
        # Only the "need" indicator remains, so its weight is re-scaled to 100%.
        self.assertEqual(result["score"], 25.0)
        skipped = [i for i in result["indicators"] if not i["available"]]
        self.assertEqual(len(skipped), 3)
        self.assertTrue(all(i["effective_weight"] == 0 for i in skipped))

    def test_missing_total_families_uses_documented_estimate(self):
        result = self.analyse(total_families=None, population=4500,
                              families_needing_assistance=100)
        self.assertEqual(result["households_basis"], "estimated")
        self.assertEqual(result["households"], 1000)          # 4500 / 4.5
        self.assertEqual(result["pct_need"], 10.0)

    def test_need_percentage_is_capped_at_100(self):
        result = self.analyse(population=100, total_families=None,
                              families_needing_assistance=100)
        self.assertLessEqual(result["pct_need"], 100.0)

    def test_effective_weights_sum_to_one(self):
        for changes in ({}, {"avg_household_income": None},
                        {"food_accessibility": None, "nearby_centers": None}):
            result = self.analyse(**changes)
            self.assertAlmostEqual(sum(i["effective_weight"] for i in result["indicators"]),
                                   1.0, places=2)

    def test_nearest_center_distance(self):
        centers = [{"id": 1, "name": "A", "latitude": 12.9, "longitude": 77.6},
                   {"id": 2, "name": "B", "latitude": 13.9, "longitude": 77.6}]
        result = scoring.analyse_community(dict(self.BASE), centers)
        self.assertEqual(result["nearest_center"]["name"], "A")
        self.assertEqual(result["nearest_center"]["distance_km"], 0.0)
        one_degree = scoring.haversine_km(12.0, 77.0, 13.0, 77.0)
        self.assertAlmostEqual(one_degree, 111.2, delta=0.5)

    def test_validate_function_directly(self):
        clean, errors = validate_community(valid_payload())
        self.assertEqual(errors, {})
        self.assertEqual(clean["population"], 3000)
        self.assertEqual(clean["latitude"], 12.95)


class InitScriptTests(unittest.TestCase):
    def test_init_db_creates_once_and_resets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "sub", "new.db")
            self.assertTrue(db.init_db(path))          # first run loads sample data
            self.assertFalse(db.init_db(path))         # second run changes nothing
            self.assertTrue(db.init_db(path, reset=True))   # reset rebuilds


if __name__ == "__main__":
    unittest.main(verbosity=2)
