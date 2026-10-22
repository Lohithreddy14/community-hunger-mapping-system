# Project Exhibition Poster: Community Hunger Mapping System (CHMS)

> **Format Specification:** Standard Academic Poster (36" x 48" or A0 Landscape/Portrait)  
> **Target Event:** Annual Engineering Project Exhibition / Capstone Showcase  

---

```
+---------------------------------------------------------------------------------------------------------+
|                                    COMMUNITY HUNGER MAPPING SYSTEM                                      |
|            A GIS-Based Decision-Support Platform for Food Vulnerability & Relief Coordination           |
|                                                                                                         |
| Department of Computer Science & Engineering | Academic Mini-Project Exhibition                         |
+----------------------------------------------------+----------------------------------------------------+
| 1. PROBLEM & MOTIVATION                            | 4. SYSTEM ARCHITECTURE                              |
| - Food aid distribution is often uncoordinated.    | [Browser UI: Bootstrap 5 + Leaflet.js]             |
| - NGOs lack geographic visibility of needy areas.  |                      | (REST JSON API)             |
| - Commercial GIS suites are expensive and complex. | [Application Layer: Python 3.10+ & Flask 3.0]      |
| - Need: Low-cost, fast, transparent decision tool. |                      | (Parameterized Queries)     |
|                                                    | [Persistence Layer: SQLite3 Relational Database]   |
| 2. CORE OBJECTIVES                                 +----------------------------------------------------+
| - Spatial hunger vulnerability index (0 to 100).   | 5. GIS MAPPING & HAVERSINE PROXIMITY                |
| - Real-time interactive OpenStreetMap interface.   | - Zero-cost open-source mapping (Leaflet.js & OSM).|
| - Dual-mode Food Center registration (Quick Add).  | - Layer filtering: Both / Communities / Centers.   |
| - Offline geodesic distance calculation.           | - Spherical Haversine distance engine:             |
| - Verification and operational status tracking.    |   d = 2R * atan2(sqrt(a), sqrt(1-a))               |
+----------------------------------------------------+----------------------------------------------------+
| 3. TRANSPARENT VULNERABILITY SCORING               | 6. CENTER MANAGEMENT & DUAL WORKFLOWS              |
| Formula: Score = Sum(w_i * R_i)                    | [Quick Add Mode (~15s)]                            |
|                                                    | - Requires: Name, Community, Phone.                |
| Indicators & Weights:                              | - Auto-inherits community coordinates.             |
| - Families in Need Ratio (45%)                     |                                                    |
| - Food Accessibility Rating (25%)                  | [Comprehensive 5-Section Registration]             |
| - Nearby Food Centers Count (20%)                  | - Interactive Leaflet location picker.             |
| - Average Household Income (10%)                   | - Live distance calculation (km).                  |
|                                                    | - Contact action suite (Call, WhatsApp, Email).    |
| Dynamic Rescaling: Missing metrics do not bias     | - Operating schedules, meal types, and diets.      |
| results; weights of active indicators rescale to 1.| - Verification audit lifecycle tracking.           |
+----------------------------------------------------+----------------------------------------------------+
| 7. SYSTEM PERFORMANCE & VERIFICATION               | 8. RESULTS & CONCLUSION                            |
| - 38 Automated Unit Tests (100% Passed).           | - Successfully identifies spatial food deserts.    |
| - 16 End-to-End Workflow Checks (100% Passed).     | - Accelerates center registration by over 70%.     |
| - Sub-100ms API response time.                     | - Operates completely offline / air-gapped.        |
| - Zero paid API keys or proprietary subscriptions. | - Sustainable, reliable community decision tool.   |
+----------------------------------------------------+----------------------------------------------------+
```

---

### Detailed Poster Text Content Blocks

#### Block 1: Introduction & Problem Context
Urban food distribution frequently encounters coordination failures: relief camps cluster near well-connected roads while remote, vulnerable settlements remain neglected. The Community Hunger Mapping System bridges this gap by unifying demographic need indicators with resource tracking on an interactive GIS map.

#### Block 2: Key System Capabilities
- **Zero-Cost Cartography:** Full GIS interactivity powered by Leaflet.js and OpenStreetMap without requiring commercial credit cards or API keys.
- **Dual-Workflow Center Registration:** Supports both high-speed emergency entry ($<15$ seconds) and exhaustive multi-section organizational profiling.
- **Explainable Scoring Engine:** Mathematically defined vulnerability calculation that rescales dynamically when optional data is absent.
- **Live Contact Integration:** Direct one-click communication triggers (`tel:`, `mailto:`, `https://wa.me/`) connecting donors with food distribution directors.

#### Block 3: Vulnerability Classification Matrix

| Vulnerability Tier | Composite Score Range | Cartographic Color | Recommended Humanitarian Action |
|---|---|---|---|
| **Higher** | $65.0 - 100.0$ | Crimson Red | Urgent relief dispatch; establish new food kitchen |
| **Moderate** | $35.0 - 64.9$ | Amber Yellow | Periodic monitoring; expand distribution schedules |
| **Lower** | $0.0 - 34.9$ | Forest Green | Sufficient coverage; maintain standard operations |

#### Block 4: Technical Specifications & Verification
- **Backend:** Python 3.10+, Flask 3.0+, SQLite3 with Foreign Key integrity.
- **Frontend:** Bootstrap 5.3, Vanilla JavaScript (ES6+), Leaflet.js 1.9.4.
- **Test Metrics:** 38 Unit tests + 16 integration checks executing in under 5 seconds.
- **Deployment:** Single command bootstrap (`run_windows.bat` or `python app.py`).
