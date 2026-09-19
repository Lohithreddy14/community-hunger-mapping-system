"""
app.py - Flask backend for the Community Hunger Mapping System (Review 2 prototype).

How the parts talk to each other
--------------------------------
  Browser (HTML + CSS + JavaScript + Leaflet)
        |   1. page requests  (GET /, /map, /add, ...)  -> Flask returns HTML
        |   2. data requests  (fetch('/api/...'))        -> Flask returns JSON
        v
  Flask (this file)  --uses-->  scoring.py (vulnerability analysis)
        |            --uses-->  validation.py (input checks)
        v
  SQLite database (database/community_hunger.db) via db.py

Run with:  python app.py    then open  http://127.0.0.1:5000
"""

from flask import Blueprint, Flask, jsonify, render_template, request

import db
import scoring
from validation import validate_community

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


def load_centers():
    rows = db.get_db().execute("SELECT * FROM food_centers ORDER BY id").fetchall()
    centers = [dict(row) for row in rows]
    for center in centers:
        center["is_sample"] = bool(center["is_sample"])
    return centers


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


# ---------------------------------------------------------------------------
# API: dashboard statistics
# ---------------------------------------------------------------------------
@bp.route("/api/stats")
def api_stats():
    communities = load_communities()
    centers = load_centers()

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
# API: food-support centers and analysis
# ---------------------------------------------------------------------------
@bp.route("/api/centers")
def api_centers():
    return jsonify(load_centers())


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

    # Create the database (and load the sample data) on the very first start.
    db.init_db(app.config["DATABASE"])

    app.teardown_appcontext(db.close_db)
    app.register_blueprint(bp)
    return app


app = create_app()

if __name__ == "__main__":
    print("Community Hunger Mapping System is starting...")
    print("Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.")
    app.run(host="127.0.0.1", port=5000, debug=True)
