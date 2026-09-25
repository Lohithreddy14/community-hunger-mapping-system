"""
tests/test_food_support_centers.py - Automated tests for Food-Support Center features.

Tests all workflows:
- Quick Add mode without coordinates
- Full registration with map coordinates and distance calculation
- Center listing, search, and filtering
- Center details retrieval
- Edit center information
- Updating verification status (Contacted, Verified)
- Deletion
- Dashboard center statistics
- Input validation and security checks
- Data survival across application restart
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
import db


class FoodSupportCenterTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test_centers.db")
        self.app = create_app({"DATABASE": self.db_path, "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pages_load(self):
        """Test all Food Support Center pages render with status 200."""
        self.assertEqual(self.client.get("/centers").status_code, 200)
        self.assertEqual(self.client.get("/centers/add").status_code, 200)
        self.assertEqual(self.client.get("/centers/1").status_code, 200)
        self.assertEqual(self.client.get("/centers/1/edit").status_code, 200)
        self.assertEqual(self.client.get("/centers/9999").status_code, 404)

    def test_quick_add_center_without_typing_coordinates(self):
        """Test quick add workflow using community reference coordinates."""
        # Community 1 exists from sample data (Lakeview Colony)
        comm1 = self.client.get("/api/communities/1").get_json()

        payload = {
            "center_name": "Seva Community Kitchen",
            "center_type": "Community Kitchen",
            "community_id": 1,
            "phone_number": "+91 98450 99887",
            "address": "Opposite Lakeview Bus Stand",
            "website": "https://seva-kitchen.example.org",
            "description": "Daily warm meals for the needy.",
        }

        response = self.client.post("/api/centers", json=payload)
        self.assertEqual(response.status_code, 201)

        center = response.get_json()
        self.assertEqual(center["center_name"], "Seva Community Kitchen")
        self.assertEqual(center["phone_number"], "+91 98450 99887")
        self.assertEqual(center["community_id"], 1)
        self.assertEqual(center["community_name"], comm1["name"])

        # Coordinates should automatically match community 1
        self.assertAlmostEqual(center["latitude"], comm1["latitude"], places=4)
        self.assertAlmostEqual(center["longitude"], comm1["longitude"], places=4)
        self.assertEqual(center["location_source"], "community_reference")
        self.assertTrue(center["is_provisional_location"])

        # Initial status should be Newly Added and unverified
        self.assertEqual(center["information_status"], "Newly Added")
        self.assertFalse(center["is_sample"])

        # Verify record is retrievable by ID
        get_res = self.client.get(f"/api/centers/{center['id']}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()["center_name"], "Seva Community Kitchen")

    def test_add_center_with_actual_coordinates_and_distance(self):
        """Test registering center with pinpointed coordinates and distance calculation."""
        comm1 = self.client.get("/api/communities/1").get_json()

        # Coordinates slightly offset from community 1
        payload = {
            "center_name": "Hope Food Bank",
            "center_type": "Food Bank",
            "community_id": 1,
            "latitude": comm1["latitude"] + 0.01,
            "longitude": comm1["longitude"] + 0.01,
            "location_source": "actual",
            "phone_number": "+91 98450 77665",
            "address": "45 Market Cross Road",
            "food_support_types": ["Groceries", "Food Packages"],
            "registration_required": "Yes",
            "availability_status": "Yes",
        }

        response = self.client.post("/api/centers", json=payload)
        self.assertEqual(response.status_code, 201)
        center = response.get_json()

        self.assertEqual(center["location_source"], "actual")
        self.assertFalse(center["is_provisional_location"])
        # Distance should be positive float around 1.5 km
        self.assertIsNotNone(center["distance_to_community_km"])
        self.assertGreater(center["distance_to_community_km"], 0.5)
        self.assertLess(center["distance_to_community_km"], 3.0)

    def test_update_center_and_edit_phone(self):
        """Test updating center details."""
        created = self.client.post("/api/centers", json={
            "center_name": "Relief Hub",
            "community_id": 1,
            "phone_number": "+91 98450 11111",
        }).get_json()

        updated_payload = {
            "center_name": "Relief Hub Updated",
            "community_id": 1,
            "phone_number": "+91 98450 22222",
            "website": "https://reliefhub.example.org",
            "address": "New Location Address",
            "operating_hours": "9:00 AM - 5:00 PM",
        }

        put_res = self.client.put(f"/api/centers/{created['id']}", json=updated_payload)
        self.assertEqual(put_res.status_code, 200)

        one = put_res.get_json()
        self.assertEqual(one["center_name"], "Relief Hub Updated")
        self.assertEqual(one["phone_number"], "+91 98450 22222")
        self.assertEqual(one["website"], "https://reliefhub.example.org")
        self.assertEqual(one["address"], "New Location Address")
        self.assertEqual(one["operating_hours"], "9:00 AM - 5:00 PM")

    def test_status_actions_mark_contacted_and_verified(self):
        """Test verification status workflow with mark_contacted and mark_verified."""
        created = self.client.post("/api/centers", json={
            "center_name": "Follow-Up Center",
            "community_id": 1,
            "phone_number": "+91 98450 33333",
        }).get_json()

        self.assertEqual(created["information_status"], "Newly Added")

        # 1. Mark as contacted
        patch_res = self.client.patch(f"/api/centers/{created['id']}/status", json={
            "action": "mark_contacted",
            "contacted_by": "Volunteer Rahul",
            "contact_notes": "Called coordinator, confirmed meal distribution timing.",
            "last_contacted_date": "2026-09-25",
        })
        self.assertEqual(patch_res.status_code, 200)
        c_contacted = patch_res.get_json()
        self.assertEqual(c_contacted["information_status"], "Contacted")
        self.assertEqual(c_contacted["contacted_by"], "Volunteer Rahul")
        self.assertEqual(c_contacted["last_contacted_date"], "2026-09-25")

        # 2. Mark as verified
        patch_res2 = self.client.patch(f"/api/centers/{created['id']}/status", json={
            "action": "mark_verified",
            "verification_notes": "Official registration certificate reviewed.",
        })
        self.assertEqual(patch_res2.status_code, 200)
        c_verified = patch_res2.get_json()
        self.assertEqual(c_verified["information_status"], "Verified")
        self.assertEqual(c_verified["verification_notes"], "Official registration certificate reviewed.")

    def test_search_and_filter_centers(self):
        """Test searching and filtering centers."""
        # Create two centers
        self.client.post("/api/centers", json={
            "center_name": "Alpha Food Bank",
            "center_type": "Food Bank",
            "community_id": 1,
            "phone_number": "+91 98450 44441",
            "availability_status": "Yes",
        })
        self.client.post("/api/centers", json={
            "center_name": "Beta Community Kitchen",
            "center_type": "Community Kitchen",
            "community_id": 2,
            "phone_number": "+91 98450 44442",
            "availability_status": "No",
        })

        # Search by name
        res = self.client.get("/api/centers?search=Alpha").get_json()
        names = [c["center_name"] for c in res]
        self.assertIn("Alpha Food Bank", names)
        self.assertNotIn("Beta Community Kitchen", names)

        # Filter by community
        res_comm = self.client.get("/api/centers?community_id=2").get_json()
        self.assertTrue(all(c["community_id"] == 2 for c in res_comm))

        # Filter by center_type
        res_type = self.client.get("/api/centers?center_type=Community+Kitchen").get_json()
        self.assertTrue(all(c["center_type"] == "Community Kitchen" for c in res_type))

        # Filter by availability
        res_avail = self.client.get("/api/centers?availability=No").get_json()
        self.assertTrue(all(c["availability_status"] == "No" for c in res_avail))

    def test_delete_center(self):
        """Test deleting a center."""
        created = self.client.post("/api/centers", json={
            "center_name": "Temporary Relief Post",
            "community_id": 1,
            "phone_number": "+91 98450 55555",
        }).get_json()

        del_res = self.client.delete(f"/api/centers/{created['id']}")
        self.assertEqual(del_res.status_code, 200)

        # Ensure subsequent get returns 404
        self.assertEqual(self.client.get(f"/api/centers/{created['id']}").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/centers/{created['id']}").status_code, 404)

    def test_dashboard_center_statistics(self):
        """Test center statistics in /api/stats and /api/center-stats."""
        before = self.client.get("/api/stats").get_json()
        initial_total = before["total_centers"]

        # Add one new center
        created = self.client.post("/api/centers", json={
            "center_name": "Stats Test Center",
            "community_id": 1,
            "phone_number": "+91 98450 66666",
        }).get_json()

        after = self.client.get("/api/stats").get_json()
        self.assertEqual(after["total_centers"], initial_total + 1)
        self.assertGreaterEqual(after["awaiting_contact_centers"], 1)

        # Verify recent centers list includes newly added center
        recent_names = [c["center_name"] for c in after["recent_centers"]]
        self.assertIn("Stats Test Center", recent_names)

        # Dedicated stats endpoint
        c_stats = self.client.get("/api/center-stats").get_json()
        self.assertEqual(c_stats["total"], initial_total + 1)

    def test_validation_errors(self):
        """Test backend validation and error messages."""
        # Missing center name
        res1 = self.client.post("/api/centers", json={
            "phone_number": "+91 98450 12345",
            "community_id": 1,
        })
        self.assertEqual(res1.status_code, 400)
        self.assertIn("center_name", res1.get_json()["errors"])

        # Missing phone number
        res2 = self.client.post("/api/centers", json={
            "center_name": "No Phone Center",
            "community_id": 1,
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("phone_number", res2.get_json()["errors"])

        # Invalid phone number (too short / characters)
        res3 = self.client.post("/api/centers", json={
            "center_name": "Bad Phone Center",
            "community_id": 1,
            "phone_number": "123",
        })
        self.assertEqual(res3.status_code, 400)
        self.assertIn("phone_number", res3.get_json()["errors"])

        # Invalid community ID
        res4 = self.client.post("/api/centers", json={
            "center_name": "Invalid Comm Center",
            "community_id": 99999,
            "phone_number": "+91 98450 12345",
        })
        self.assertEqual(res4.status_code, 400)
        self.assertIn("community_id", res4.get_json()["errors"])

        # Coordinates out of range
        res5 = self.client.post("/api/centers", json={
            "center_name": "Off World Center",
            "phone_number": "+91 98450 12345",
            "latitude": 999.0,
            "longitude": 77.0,
        })
        self.assertEqual(res5.status_code, 400)
        self.assertIn("latitude", res5.get_json()["errors"])

    def test_data_survives_restart(self):
        """Test that user registered centers survive application restart."""
        self.client.post("/api/centers", json={
            "center_name": "Persistent Food Bank",
            "community_id": 1,
            "phone_number": "+91 98450 88888",
        })

        # Recreate application on same database path
        restarted_app = create_app({"DATABASE": self.db_path, "TESTING": True})
        restarted_client = restarted_app.test_client()

        centers = restarted_client.get("/api/centers").get_json()
        names = [c.get("center_name") or c.get("name") for c in centers]
        self.assertIn("Persistent Food Bank", names)


if __name__ == "__main__":
    unittest.main()
