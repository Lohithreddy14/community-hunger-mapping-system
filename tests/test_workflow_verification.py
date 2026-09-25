"""
tests/test_workflow_verification.py - Tests all 16 required workflows against the real application.
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
import db


def run_16_workflow_checks():
    print("==================================================")
    print("RUNNING 16 WORKFLOW VERIFICATION CHECKS")
    print("==================================================")

    app = create_app({"DATABASE": db.DB_PATH, "TESTING": True})
    client = app.test_client()

    # Step 1: Open the Food-Support Centers page
    print("\n[Step 1] Opening Food-Support Centers page (/centers)...")
    res1 = client.get("/centers")
    assert res1.status_code == 200, f"Failed step 1: {res1.status_code}"
    assert "Food Support Centers" in res1.get_data(as_text=True)
    print("  -> PASSED: /centers loaded successfully with status 200.")

    # Step 2: Select an existing community
    print("\n[Step 2] Fetching existing communities...")
    res2 = client.get("/api/communities")
    assert res2.status_code == 200
    communities = res2.get_json()
    assert len(communities) > 0, "No communities in database!"
    comm1 = communities[0]
    print(f"  -> PASSED: Selected community '{comm1['name']}' (ID: {comm1['id']}, Lat: {comm1['latitude']}, Lon: {comm1['longitude']}).")

    # Step 3 & 4: Quick-add a center without typing coordinates and save
    print("\n[Step 3 & 4] Quick-adding center without typing coordinates...")
    quick_payload = {
        "center_name": "Seva Bhojan Center",
        "center_type": "Community Kitchen",
        "community_id": comm1["id"],
        "phone_number": "+91 98450 77112",
        "address": "Near Community Bus Stop",
        "description": "Daily food relief for local families."
    }
    res3 = client.post("/api/centers", json=quick_payload)
    assert res3.status_code == 201, f"Failed step 3/4: {res3.status_code} {res3.get_data(as_text=True)}"
    created_center = res3.get_json()
    center_id = created_center["id"]
    assert created_center["center_name"] == "Seva Bhojan Center"
    assert created_center["location_source"] == "community_reference"
    assert abs(created_center["latitude"] - comm1["latitude"]) < 1e-4
    assert abs(created_center["longitude"] - comm1["longitude"]) < 1e-4
    assert created_center["information_status"] == "Newly Added"
    print(f"  -> PASSED: Center created (ID: {center_id}) with auto-filled coordinates from community '{comm1['name']}'.")

    # Step 5: Confirm that the center is stored in SQLite
    print("\n[Step 5] Checking physical SQLite database...")
    conn = sqlite3.connect(db.DB_PATH)
    try:
        row = conn.execute("SELECT id, center_name, phone_number, community_id, latitude, longitude, information_status FROM food_support_centers WHERE id = ?", (center_id,)).fetchone()
        assert row is not None, "Center not found in SQLite table food_support_centers!"
        assert row[1] == "Seva Bhojan Center"
        print(f"  -> PASSED: Stored directly in SQLite: ID={row[0]}, Name='{row[1]}', Status='{row[6]}'.")
    finally:
        conn.close()

    # Step 6: Confirm that the center appears in the center list
    print("\n[Step 6] Confirming center appears in center list (/api/centers)...")
    res6 = client.get("/api/centers")
    all_centers = res6.get_json()
    found = any(c["id"] == center_id for c in all_centers)
    assert found, "Center missing from /api/centers listing!"
    print("  -> PASSED: Center appears in the full center listing.")

    # Step 7: Open its details
    print(f"\n[Step 7] Opening center details (/centers/{center_id} and /api/centers/{center_id})...")
    res7_page = client.get(f"/centers/{center_id}")
    assert res7_page.status_code == 200
    res7_api = client.get(f"/api/centers/{center_id}")
    assert res7_api.status_code == 200
    detail = res7_api.get_json()
    assert detail["phone_number"] == "+91 98450 77112"
    print("  -> PASSED: Center details page and API endpoint returned 200.")

    # Step 8 & 9: Edit the phone number and add its website
    print("\n[Step 8 & 9] Editing phone number and adding website...")
    update_payload = {
        "center_name": "Seva Bhojan Center",
        "community_id": comm1["id"],
        "phone_number": "+91 98450 99999",
        "website": "https://sevabhojan.example.org",
        "address": "123 Main Bazaar Road",
    }
    res8 = client.put(f"/api/centers/{center_id}", json=update_payload)
    assert res8.status_code == 200
    updated = res8.get_json()
    assert updated["phone_number"] == "+91 98450 99999"
    assert updated["website"] == "https://sevabhojan.example.org"
    print(f"  -> PASSED: Phone updated to {updated['phone_number']}, website set to {updated['website']}.")

    # Step 10: Update its verification status
    print("\n[Step 10] Updating verification status...")
    patch1 = client.patch(f"/api/centers/{center_id}/status", json={
        "action": "mark_contacted",
        "contacted_by": "Field Officer Ananya",
        "contact_notes": "Spoke to kitchen manager; food distributed daily 12-2 PM."
    })
    assert patch1.status_code == 200
    assert patch1.get_json()["information_status"] == "Contacted"

    patch2 = client.patch(f"/api/centers/{center_id}/status", json={
        "action": "mark_verified",
        "verification_notes": "Verified NGO registration documents and physical location."
    })
    assert patch2.status_code == 200
    assert patch2.get_json()["information_status"] == "Verified"
    print("  -> PASSED: Verification status updated to Contacted, then Verified.")

    # Step 11: Search for the center
    print("\n[Step 11] Searching for the center by keyword...")
    search_res = client.get("/api/centers?search=Bhojan")
    assert search_res.status_code == 200
    search_items = search_res.get_json()
    assert any(c["id"] == center_id for c in search_items)
    print(f"  -> PASSED: Found {len(search_items)} result(s) searching for 'Bhojan'.")

    # Step 12: Filter centers by community
    print(f"\n[Step 12] Filtering centers by community ID {comm1['id']}...")
    filter_res = client.get(f"/api/centers?community_id={comm1['id']}")
    assert filter_res.status_code == 200
    comm_centers = filter_res.get_json()
    assert any(c["id"] == center_id for c in comm_centers)
    print(f"  -> PASSED: Filter returned {len(comm_centers)} center(s) for community ID {comm1['id']}.")

    # Step 13: Display the center on the GIS map when coordinates are available
    print("\n[Step 13] Checking GIS map coordinates availability...")
    map_res = client.get("/map")
    assert map_res.status_code == 200
    centers_for_map = client.get("/api/centers").get_json()
    this_center = next(c for c in centers_for_map if c["id"] == center_id)
    assert this_center["latitude"] is not None and this_center["longitude"] is not None
    print(f"  -> PASSED: Center has map coordinates: ({this_center['latitude']}, {this_center['longitude']}).")

    # Step 14: Confirm that dashboard statistics update
    print("\n[Step 14] Checking dashboard statistics update...")
    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200
    stats = stats_res.get_json()
    assert stats["total_centers"] >= 6  # 5 samples + at least 1 added
    assert stats["verified_centers"] >= 1
    recent_ids = [c["id"] for c in stats["recent_centers"]]
    assert center_id in recent_ids
    print(f"  -> PASSED: Dashboard live stats updated: Total Centers={stats['total_centers']}, Verified={stats['verified_centers']}.")

    # Step 15: Restart the Flask server and verify that the record remains saved
    print("\n[Step 15] Simulating Flask server restart...")
    restarted_app = create_app({"DATABASE": db.DB_PATH, "TESTING": True})
    restarted_client = restarted_app.test_client()
    res_after_restart = restarted_client.get(f"/api/centers/{center_id}")
    assert res_after_restart.status_code == 200
    persisted = res_after_restart.get_json()
    assert persisted["center_name"] == "Seva Bhojan Center"
    assert persisted["information_status"] == "Verified"
    print("  -> PASSED: Record successfully persisted across simulated restart.")

    # Step 16: Confirm that all existing project features continue working
    print("\n[Step 16] Verifying all existing project features...")
    for route in ("/", "/map", "/add", "/communities", "/api/stats", "/api/communities", "/api/analysis"):
        r = restarted_client.get(route)
        assert r.status_code == 200, f"Route {route} failed with {r.status_code}"
    # Verify scoring model works
    analysis = restarted_client.get("/api/analysis").get_json()
    assert len(analysis["results"]) >= 10
    print("  -> PASSED: All existing routes, analysis, scoring, and pages function perfectly.")

    # Clean up test center from db so it stays clean
    client.delete(f"/api/centers/{center_id}")
    print(f"\n[Cleanup] Test center {center_id} removed from database.")

    print("\n==================================================")
    print("ALL 16 WORKFLOW CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    run_16_workflow_checks()
