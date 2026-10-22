# Top 25 Viva Examination Questions & Answers
## Community Hunger Mapping System (CHMS)

This document provides model academic answers to the top 25 viva questions across technical, architectural, mathematical, GIS, and ethical domains.

---

### CATEGORY 1: ARCHITECTURAL & SYSTEM DESIGN

#### Q1: Why did you choose Python Flask instead of Django or Node.js?
**Answer:** Flask is a lightweight WSGI microframework that offers architectural minimalism and low overhead. For a specialized GIS decision-support tool, Flask provides complete granular control over routing, custom SQL parameterization, and JSON serialization without the overhead of Django’s heavyweight built-in ORM or administrative bloat. Compared to Node.js, Python offers superior mathematical libraries and cleaner syntax for algorithmic operations such as our vulnerability scoring and Haversine distance computations.

#### Q2: What architectural design pattern does your project follow?
**Answer:** The project follows a hybrid Model-View-Controller (MVC) and RESTful API architecture:
- **Model:** Data persistence managed in `db.py` via SQLite3 with structured schemas, foreign keys, and views.
- **View:** HTML5/Bootstrap templates rendered via Jinja2 along with dynamic Leaflet.js client components.
- **Controller:** Flask route handlers in `app.py` that orchestrate business logic, coordinate validation (`validation.py`), and invoke mathematical scoring (`scoring.py`).
- **REST Endpoints:** Decoupled JSON endpoints (`/api/stats`, `/api/map-data`, `/api/centers`) allow asynchronous frontend updates without full-page reloads.

#### Q3: Why did you select SQLite over client-server DBMSs like MySQL or PostgreSQL?
**Answer:** SQLite is an in-process, zero-configuration, ACID-compliant transactional relational engine stored in a single cross-platform file. For local community organizations, disaster response deployments, and academic evaluation, SQLite eliminates the need to configure and maintain persistent background daemon services, user permissions, and port networking. For larger multi-tenant enterprise deployments, our data access layer (`db.py`) is modular and can readily be adapted to PostgreSQL/PostGIS.

#### Q4: How does your database ensure backward compatibility with earlier code referencing the legacy `food_centers` table?
**Answer:** We implemented a database migration in `db.py` that renames or restructures the legacy table into `food_support_centers`, and simultaneously creates an SQLite VIEW named `food_centers`. To support legacy insert operations, we attached an `INSTEAD OF INSERT` trigger on the view that redirects legacy columns into the new normalized schema with appropriate defaults.

---

### CATEGORY 2: GIS & SPATIAL MAPPING

#### Q5: How is the interactive map implemented without paying for Google Maps API keys?
**Answer:** The GIS engine is built using **Leaflet.js** (an open-source JavaScript cartography library) combined with **OpenStreetMap (OSM)** raster tiles. Leaflet handles client-side panning, zooming, marker clustering, and coordinate projections, while OSM provides community-maintained, free-to-use map tiles. This completely eliminates proprietary API keys, credit card requirements, and per-query rate limiting.

#### Q6: How does the map handle simultaneous display of both communities and food centers?
**Answer:** The client script `static/js/map.js` initializes separate Leaflet `L.layerGroup()` instances: one for community vulnerability circles and another for food-support center markers. The UI provides a segmented layer control allowing users to view **Both Layers**, **Communities Only**, or **Food Centers Only** dynamically without re-querying the backend.

#### Q7: What is the purpose of the custom SVG map pins used for Food Support Centers?
**Answer:** Rather than standard generic pins, centers use custom Leaflet `L.divIcon` markers containing an SVG fork-and-knife motif. The outer badge is dynamically styled based on verification status (e.g., emerald green for *Verified*, amber orange for *Contacted*, slate gray for *Unverified*), allowing immediate visual assessment on the cartographic canvas.

#### Q8: What coordinate reference system (CRS) does the platform use?
**Answer:** The platform uses the standard **WGS 84 (EPSG:4326)** coordinate reference system (latitude and longitude in decimal degrees) for storage and API transfers. Leaflet automatically projects these coordinates into **Web Mercator (EPSG:3857)** when rendering OpenStreetMap raster tiles.

---

### CATEGORY 3: MATHEMATICAL MODEL & ALGORITHMS

#### Q9: What is the mathematical formulation of the Vulnerability Score?
**Answer:** The composite Vulnerability Score ($S$) is a normalized weighted multi-criteria index calculated as:
$$S = \sum_{i=1}^{n} w_i \cdot R_i$$
Where $R_i \in [0, 100]$ represents the transformed risk score for indicator $i$, and $w_i$ is its normalized weight.
The four indicators are:
1. **Assistance Need Ratio ($w = 0.45$):** $R_1 = \min(P_{\text{need}} / 40, 1.0) \times 100$
2. **Food Accessibility ($w = 0.25$):** Good = 0, Moderate = 50, Poor = 100
3. **Nearby Centers Proximity ($w = 0.20$):** $\ge 3$ centers = 0, 2 = 30, 1 = 60, 0 = 100
4. **Average Income ($w = 0.10$):** Linear scale between Rs. 10,000 ($R=100$) and Rs. 40,000 ($R=0$)

#### Q10: How does your scoring model handle missing optional values without introducing bias?
**Answer:** Instead of substituting missing indicators with arbitrary averages or zeros (which would falsely deflate or inflate risk), the algorithm employs **Dynamic Weight Rescaling**:
$$w_i' = \frac{w_i}{\sum_{j \in \text{Available}} w_j}$$
The weights of the remaining active indicators are rescaled so their sum strictly equals $1.0$.

#### Q11: Explain the Haversine distance formula and why it was chosen.
**Answer:** The Haversine formula calculates the great-circle distance between two coordinate pairs on a sphere:
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right), \quad d = R \cdot c \quad (R = 6371 \text{ km})$$
It was chosen because it executes instantly in $\mathcal{O}(1)$ time offline without invoking third-party distance matrix APIs.

#### Q12: Why are the vulnerability score categories partitioned at 35 and 65?
**Answer:** The scale spans 0 to 100. Partitioning at $<35$ (Lower), $35-64.9$ (Moderate), and $\ge 65$ (Higher) creates balanced, defensible operational tiers. A community only enters the *Higher* tier if it demonstrates acute distress across multiple indicators simultaneously.

---

### CATEGORY 4: FOOD-SUPPORT CENTER MANAGEMENT & WORKFLOWS

#### Q13: What is the difference between Quick Add and Comprehensive Registration?
**Answer:** 
- **Quick Add:** Built for rapid field entry ($<15$ seconds). Requires only Center Name, Community Area, and Primary Phone. Geographic coordinates are automatically inherited from the community's known reference centroid.
- **Comprehensive Registration:** A 5-section workflow capturing detailed profiles, interactive Leaflet coordinate picking, distance calculations, operating schedules, meal types, contact personnel, and verification tracking.

#### Q14: How does the system prevent misleading location claims when Quick Add is used?
**Answer:** The database stores a boolean flag `is_provisional_location` or checks if coordinates match the parent community centroid. In the UI and API, the coordinates are explicitly labeled as *"Reference location derived from Community"* rather than claiming to represent the physical building.

#### Q15: What verification lifecycle does a food center follow?
**Answer:** Centers transition through four audited states:
1. `Newly Added / Unverified`: Default state upon initial submission.
2. `Contacted`: Field officer has communicated with the representative.
3. `Verified`: Operating status, address, and meal distribution confirmed.
4. `Follow-up Needed`: Flagged for periodic re-audit or schedule clarification.

---

### CATEGORY 5: SECURITY, VALIDATION & INTEGRITY

#### Q16: How does the system defend against SQL Injection?
**Answer:** All database operations in `db.py` use parameterized SQL statements with `?` placeholders (e.g., `cursor.execute("SELECT * FROM communities WHERE id = ?", (community_id,))`). User input is passed as parameter tuples to SQLite’s compiled query engine, preventing any user input from altering SQL command syntax.

#### Q17: How is Cross-Site Scripting (XSS) mitigated in the user interface?
**Answer:** Jinja2 contextual auto-escaping is enabled by default. Any HTML tags or scripts submitted in text fields are escaped into harmless HTML entities (`&lt;script&gt;`). When JSON data is passed to client scripts, it is serialized using Flask’s `tojson` filter.

#### Q18: What input validation constraints are enforced on demographic data?
**Answer:** 
1. Total population must be $\ge 1$.
2. Families needing assistance cannot exceed total population ($F_{\text{need}} \le P_{\text{total}}$).
3. If total families is provided, $F_{\text{need}} \le \text{Total Families}$.
4. Latitude must lie in $[-90.0, 90.0]$ and longitude in $[-180.0, 180.0]$.

#### Q19: How are phone numbers and URLs validated?
**Answer:** In `validation.py`, primary and alternative phone numbers are validated against standard telecom regex patterns allowing international formats (`+` prefix, 7 to 15 digits). URLs must specify explicit `http://` or `https://` schemes.

---

### CATEGORY 6: TESTING & QUALITY ASSURANCE

#### Q20: What automated testing approaches did you implement?
**Answer:** We implemented a two-tier testing methodology using Python’s built-in `unittest` framework:
1. **Unit Testing (`tests/test_app.py`, `tests/test_food_support_centers.py`):** 38 automated test cases covering model calculations, database triggers, API response codes, and input validation failures.
2. **Workflow Verification (`tests/test_workflow_verification.py`):** A 16-step integration test simulating real user journeys (Quick Add $\rightarrow$ Detail View $\rightarrow$ Status Update $\rightarrow$ Search $\rightarrow$ Map verification $\rightarrow$ Server restart persistence).

#### Q21: How do your tests ensure database isolation?
**Answer:** Test fixtures create a temporary, distinct SQLite database file in a sandbox directory during `setUp()` and tear it down during `tearDown()`. This guarantees that unit tests never overwrite or corrupt the development or production database.

---

### CATEGORY 7: LIMITATIONS, ETHICS & FUTURE EXTENSIONS

#### Q22: Does this system track or identify individual hungry people?
**Answer:** **No.** By design, CHMS operates exclusively on aggregated community-level figures. Storing names, addresses, or private details of individual recipients is deliberately prohibited to uphold human dignity and prevent stigmatization.

#### Q23: What are the main limitations of the current implementation?
**Answer:**
1. **Geodesic vs. Network Distance:** The Haversine formula measures straight-line distance, not actual walking or driving distance along street networks.
2. **Tile Caching:** OpenStreetMap tiles require an internet connection on initial load, unless pre-cached locally.
3. **Authentication:** The current prototype is configured for trusted administrative intranets and does not yet include role-based login tiers.

#### Q24: How would you scale this system for state-wide or national deployment?
**Answer:**
1. Migrate the database layer from SQLite to PostgreSQL with the PostGIS extension for spatial index acceleration ($R\text{-tree}$).
2. Implement Redis caching for frequently queried endpoints (`/api/map-data`, `/api/stats`).
3. Deploy behind Gunicorn WSGI workers load-balanced by NGINX.
4. Integrate Open Source Routing Machine (OSRM) for street-network routing.

#### Q25: What is the primary takeaway of this project for academic evaluation?
**Answer:** The Community Hunger Mapping System demonstrates that high-utility, reliable, and user-centric GIS decision-support platforms can be engineered entirely with open-source technologies, zero licensing fees, mathematically sound models, and verifiable software engineering practices.
