"""
app.py - Flask backend for the Community Hunger Mapping System.

How the parts talk to each other
--------------------------------
  Browser (HTML + CSS + JavaScript + Leaflet)
        |   1. page requests  (GET /, /map, /add, /communities, /centers, ...) -> Flask returns HTML
        |   2. data requests  (fetch('/api/...'))                                -> Flask returns JSON
        v
  Flask (this file)  --uses-->  scoring.py (vulnerability analysis)
        |            --uses-->  validation.py (input checks)
        v
  SQLite database (database/community_hunger.db) via db.py

Run with:  python app.py    then open  http://127.0.0.1:5000
"""

from datetime import datetime
from flask import Blueprint, Flask, jsonify, render_template, request

import db
import scoring
from validation import validate_community, validate_food_support_center

RECENT_LIMIT = 5
PRIORITY_LIMIT = 5

bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def api_error(message, status=400, errors=None):
    payload = {"error": message}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status


def load_centers(filters=None):
    """Load food-support centers from the database with optional filters."""
    return db.list_centers(db.get_db(), filters)


def get_center_or_none(center_id):
    """Retrieve a single food-support center by ID or return None."""
    return db.get_center(db.get_db(), center_id)


def present_community(row, centers):
    """Turn a database row into a dict that includes its vulnerability analysis."""
    community = dict(row)
    community["is_sample"] = bool(community["is_sample"])
    analysis = scoring.analyse_community(community, centers)
    community["analysis"] = analysis
    community["category"] = analysis["category"]["key"]
    community["score"] = analysis["score"]
    return community


def load_communities():
    centers = load_centers()
    rows = db.get_db().execute("SELECT * FROM communities ORDER BY id").fetchall()
    return [present_community(row, centers) for row in rows]


def get_community_or_none(community_id):
    row = db.get_db().execute("SELECT * FROM communities WHERE id = ?",
                              (community_id,)).fetchone()
    if row is None:
        return None
    return present_community(row, load_centers())


def read_json_body():
    """Return the parsed JSON body, or None if it is missing or malformed."""
    return request.get_json(silent=True)


# ---------------------------------------------------------------------------
# Pages (HTML)
# ---------------------------------------------------------------------------
@bp.route("/")
def dashboard():
    return render_template("dashboard.html")


@bp.route("/map")
def map_page():
    return render_template("map.html")


@bp.route("/add")
def add_community():
    return render_template("add_community.html", community_id=None)


@bp.route("/edit/<int:community_id>")
def edit_community(community_id):
    if get_community_or_none(community_id) is None:
        return render_template("404.html"), 404
    return render_template("add_community.html", community_id=community_id)


@bp.route("/communities")
def communities_page():
    return render_template("communities.html")


@bp.route("/centers")
def centers_page():
    return render_template("centers.html")


@bp.route("/centers/add")
def add_center_page():
    return render_template("add_center.html", center_id=None)


@bp.route("/centers/<int:center_id>")
def center_detail_page(center_id):
    center = get_center_or_none(center_id)
    if center is None:
        return render_template("404.html"), 404
    return render_template("center_detail.html", center_id=center_id)


@bp.route("/centers/<int:center_id>/edit")
def edit_center_page(center_id):
    center = get_center_or_none(center_id)
    if center is None:
        return render_template("404.html"), 404
    return render_template("add_center.html", center_id=center_id)


# ---------------------------------------------------------------------------
# API: dashboard statistics
# ---------------------------------------------------------------------------
@bp.route("/api/stats")
def api_stats():
    communities = load_communities()
    centers = load_centers()
    center_stats = db.get_center_stats(db.get_db())

    counts = {"lower": 0, "moderate": 0, "higher": 0}
    families = {"lower": 0, "moderate": 0, "higher": 0}
    for community in communities:
        counts[community["category"]] += 1
        families[community["category"]] += community["families_needing_assistance"]

    def summary(c):
        return {
            "id": c["id"], "name": c["name"], "population": c["population"],
            "families_needing_assistance": c["families_needing_assistance"],
            "category": c["category"], "score": c["score"],
            "is_sample": c["is_sample"], "created_at": c["created_at"],
        }

    recent = sorted(communities, key=lambda c: c["id"], reverse=True)[:RECENT_LIMIT]
    priority = sorted(communities, key=lambda c: c["score"], reverse=True)[:PRIORITY_LIMIT]

    return jsonify({
        "total_areas": len(communities),
        "total_population": sum(c["population"] for c in communities),
        "total_families_needing_assistance":
            sum(c["families_needing_assistance"] for c in communities),
        "total_centers": len(centers),
        "verified_centers": center_stats["verified"],
        "awaiting_contact_centers": center_stats["awaiting_contact"],
        "incomplete_centers": center_stats["incomplete"],
        "inactive_centers": center_stats["inactive"],
        "recent_centers": center_stats["recent"],
        "category_counts": counts,
        "families_by_category": families,
        "sample_records": sum(1 for c in communities if c["is_sample"]),
        "user_records": sum(1 for c in communities if not c["is_sample"]),
        "recent": [summary(c) for c in recent],
        "highest_scores": [summary(c) for c in priority],
    })


# ---------------------------------------------------------------------------
# API: communities
# ---------------------------------------------------------------------------
@bp.route("/api/communities", methods=["GET"])
def api_list_communities():
    communities = load_communities()
    category = request.args.get("category")
    if category:
        if category not in scoring.CATEGORIES:
            return api_error("Category must be lower, moderate or higher.")
        communities = [c for c in communities if c["category"] == category]
    return jsonify(communities)


@bp.route("/api/communities/<int:community_id>", methods=["GET"])
def api_get_community(community_id):
    community = get_community_or_none(community_id)
    if community is None:
        return api_error("Community not found.", 404)
    return jsonify(community)


@bp.route("/api/communities", methods=["POST"])
def api_create_community():
    data = read_json_body()
    if data is None:
        return api_error("The request must contain valid JSON.")
    clean, errors = validate_community(data)
    if errors:
        return api_error("Please correct the highlighted fields.", 400, errors)

    conn = db.get_db()
    new_id = db.insert_community(conn, clean, is_sample=False)
    return jsonify(get_community_or_none(new_id)), 201


@bp.route("/api/communities/<int:community_id>", methods=["PUT"])
def api_update_community(community_id):
    if get_community_or_none(community_id) is None:
        return api_error("Community not found.", 404)
    data = read_json_body()
    if data is None:
        return api_error("The request must contain valid JSON.")
    clean, errors = validate_community(data)
    if errors:
        return api_error("Please correct the highlighted fields.", 400, errors)

    db.update_community(db.get_db(), community_id, clean)
    return jsonify(get_community_or_none(community_id))


@bp.route("/api/communities/<int:community_id>", methods=["DELETE"])
def api_delete_community(community_id):
    if not db.delete_community(db.get_db(), community_id):
        return api_error("Community not found.", 404)
    return jsonify({"deleted": community_id})


# ---------------------------------------------------------------------------
# API: food-support centers
# ---------------------------------------------------------------------------
@bp.route("/api/centers", methods=["GET"])
def api_centers():
    filters = {}
    if request.args.get("search"):
        filters["search"] = request.args.get("search")
    if request.args.get("community_id"):
        try:
            filters["community_id"] = int(request.args.get("community_id"))
        except ValueError:
            pass
    if request.args.get("center_type"):
        filters["center_type"] = request.args.get("center_type")
    if request.args.get("information_status"):
        filters["information_status"] = request.args.get("information_status")
    elif request.args.get("status"):
        filters["information_status"] = request.args.get("status")
    if request.args.get("availability"):
        filters["availability_status"] = request.args.get("availability")

    return jsonify(load_centers(filters if filters else None))


@bp.route("/api/centers/<int:center_id>", methods=["GET"])
def api_get_center(center_id):
    center = get_center_or_none(center_id)
    if center is None:
        return api_error("Food-support center not found.", 404)
    return jsonify(center)


@bp.route("/api/centers", methods=["POST"])
def api_create_center():
    data = read_json_body()
    if data is None:
        return api_error("The request must contain valid JSON.")

    clean, errors = validate_food_support_center(data, allow_missing_coords=True)
    if errors:
        return api_error("Please correct the highlighted fields.", 400, errors)

    conn = db.get_db()

    community = None
    if clean.get("community_id"):
        community = get_community_or_none(clean["community_id"])
        if community is None:
            return api_error("Selected community does not exist.", 400,
                             {"community_id": "Selected community not found."})

    # If coordinates were not manually selected or typed, inherit community reference coordinates
    if clean.get("latitude") is None or clean.get("longitude") is None:
        if community:
            clean["latitude"] = community["latitude"]
            clean["longitude"] = community["longitude"]
            clean["location_source"] = "community_reference"
        else:
            return api_error("Please select an existing community or specify coordinates.", 400,
                             {"community_id": "Please select a community to associate with."})

    new_id = db.insert_center(conn, clean, is_sample=False)
    created = get_center_or_none(new_id)
    return jsonify(created), 201


@bp.route("/api/centers/<int:center_id>", methods=["PUT"])
def api_update_center(center_id):
    existing = get_center_or_none(center_id)
    if existing is None:
        return api_error("Food-support center not found.", 404)

    data = read_json_body()
    if data is None:
        return api_error("The request must contain valid JSON.")

    clean, errors = validate_food_support_center(data, allow_missing_coords=True)
    if errors:
        return api_error("Please correct the highlighted fields.", 400, errors)

    conn = db.get_db()
    community = None
    if clean.get("community_id"):
        community = get_community_or_none(clean["community_id"])
        if community is None:
            return api_error("Selected community does not exist.", 400,
                             {"community_id": "Selected community not found."})

    if clean.get("latitude") is None or clean.get("longitude") is None:
        if community:
            clean["latitude"] = community["latitude"]
            clean["longitude"] = community["longitude"]
            clean["location_source"] = "community_reference"
        else:
            clean["latitude"] = existing["latitude"]
            clean["longitude"] = existing["longitude"]

    db.update_center(conn, center_id, clean)
    return jsonify(get_center_or_none(center_id))


@bp.route("/api/centers/<int:center_id>/status", methods=["PATCH"])
def api_update_center_status(center_id):
    existing = get_center_or_none(center_id)
    if existing is None:
        return api_error("Food-support center not found.", 404)

    data = read_json_body()
    if data is None:
        return api_error("The request must contain valid JSON.")

    action = data.get("action")
    status_data = {}
    today_str = datetime.now().strftime("%Y-%m-%d")

    if action == "mark_contacted":
        status_data["information_status"] = "Contacted"
        status_data["last_contacted_date"] = data.get("last_contacted_date") or today_str
        if data.get("contacted_by"):
            status_data["contacted_by"] = str(data["contacted_by"]).strip()[:100]
        if data.get("contact_notes"):
            status_data["contact_notes"] = str(data["contact_notes"]).strip()[:1000]
        if data.get("next_followup_date"):
            status_data["next_followup_date"] = str(data["next_followup_date"]).strip()[:30]
    elif action == "mark_verified":
        status_data["information_status"] = "Verified"
        if data.get("verification_notes"):
            status_data["verification_notes"] = str(data["verification_notes"]).strip()[:1000]
    else:
        for field in ("information_status", "availability_status", "contact_attempt_date",
                      "last_contacted_date", "next_followup_date", "contacted_by",
                      "contact_notes", "information_source", "verification_notes"):
            if field in data and data[field] is not None:
                status_data[field] = str(data[field]).strip()

    db.update_center_status(db.get_db(), center_id, status_data)
    return jsonify(get_center_or_none(center_id))


@bp.route("/api/centers/<int:center_id>", methods=["DELETE"])
def api_delete_center(center_id):
    if not db.delete_center(db.get_db(), center_id):
        return api_error("Food-support center not found.", 404)
    return jsonify({"deleted": center_id})


@bp.route("/api/center-stats")
def api_center_stats():
    return jsonify(db.get_center_stats(db.get_db()))


# ---------------------------------------------------------------------------
# API: vulnerability analysis
# ---------------------------------------------------------------------------
@bp.route("/api/analysis")
def api_analysis():
    """Vulnerability analysis results for every community, plus the method used."""
    results = [{
        "id": c["id"], "name": c["name"], "score": c["score"],
        "category": c["analysis"]["category"], "indicators": c["analysis"]["indicators"],
        "indicators_used": c["analysis"]["indicators_used"],
    } for c in load_communities()]
    return jsonify({"method": scoring.methodology(), "results": results})


# ---------------------------------------------------------------------------
# Error handlers: JSON for /api/*, a friendly page for everything else
# ---------------------------------------------------------------------------
@bp.app_errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return api_error("Resource not found.", 404)
    return render_template("404.html"), 404


@bp.app_errorhandler(405)
def method_not_allowed(_error):
    return api_error("Method not allowed.", 405)


@bp.app_errorhandler(500)
def server_error(_error):
    if request.path.startswith("/api/"):
        return api_error("Unexpected server error. Check the terminal for details.", 500)
    return render_template("404.html", server_error=True), 500


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app(test_config=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db.DB_PATH
    if test_config:
        app.config.update(test_config)

    # Create or migrate database on startup
    db.init_db(app.config["DATABASE"])

    app.teardown_appcontext(db.close_db)
    app.register_blueprint(bp)
    return app


app = create_app()

if __name__ == "__main__":
    print("Community Hunger Mapping System is starting...")
    print("Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.")
    app.run(host="127.0.0.1", port=5000, debug=True)
