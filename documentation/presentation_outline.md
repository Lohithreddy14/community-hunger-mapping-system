# Presentation Outline & Viva Defense Script
## Community Hunger Mapping System (CHMS)

**Target Audience:** Project Evaluation Committee, External Examiners, Faculty Guides  
**Total Allocated Time:** 15 - 20 Minutes (10 min Presentation, 5 min Live Demonstration, 5 min Q&A)

---

### Slide-by-Slide Presentation Structure

#### Slide 1: Title & Team Information (Time: 0:30)
- **Title:** Community Hunger Mapping System: A GIS-Based Web Platform for Vulnerability Assessment & Food-Support Center Coordination
- **Project Domain:** Web-Based Geographic Information Systems (GIS), Humanitarian Computing, Decision Support Systems
- **Tech Stack:** Python (Flask), SQLite3, Leaflet.js, OpenStreetMap, Bootstrap 5
- **Presenter(s):** [Your Name / Team Members]
- **Key Message:** An accessible, zero-cost, fully functional spatial platform designed to assist aid organizations in prioritizing hunger hotspots and managing relief resources.

#### Slide 2: Problem Statement & Motivation (Time: 1:00)
- **The Challenge:** Food insecurity data is fragmented across paper ledgers, informal calls, and spreadsheets.
- **The Gap:** Relief planners cannot visualize where needy populations reside relative to where food distribution centers are located.
- **The Barrier:** Commercial GIS tools (e.g., ArcGIS, Google Maps API) are expensive, complex, and require per-query API billing.
- **The Goal:** Build an open-source, lightweight, browser-based GIS tool requiring zero paid APIs that works reliably on commodity hardware.

#### Slide 3: System Objectives & Scope (Time: 1:00)
- **Objective 1:** Relational cataloging of community demographic vulnerability indicators.
- **Objective 2:** Transparent mathematical vulnerability scoring without black-box logic.
- **Objective 3:** Dual-mode Food-Support Center management (15-second Quick Add vs. Complete 5-Section Registration).
- **Objective 4:** Interactive multi-layer GIS mapping (Leaflet.js & OpenStreetMap).
- **Objective 5:** Automated proximity estimation using the Haversine distance equation.

#### Slide 4: System Architecture & Workflow (Time: 1:30)
- **Presentation Visual:** High-level 3-tier architecture diagram.
- **Frontend Layer:** Responsive HTML5/Bootstrap 5 interface + Leaflet.js interactive maps.
- **Application Controller:** Python Flask REST API handling data validation, route orchestration, and scoring calculations.
- **Persistence Layer:** Normalized SQLite database with backward-compatible views and integrity triggers.
- **Highlight:** Clean separation of concerns with RESTful API endpoints (`/api/stats`, `/api/map-data`, `/api/centers`).

#### Slide 5: Vulnerability Scoring Methodology (Time: 2:00)
- **Explainable Multi-Indicator Formula:**
  $$\text{Score} = \sum w_i \times R_i \quad (0 \le \text{Score} \le 100)$$
- **Indicator Breakdown:**
  1. Need Percentage ($\text{weight} = 0.45$): $\min(\% / 40, 1) \times 100$
  2. Food Accessibility ($\text{weight} = 0.25$): Good (0), Moderate (50), Poor (100)
  3. Support Centers Proximity ($\text{weight} = 0.20$): $\ge 3$ (0), 2 (30), 1 (60), 0 (100)
  4. Average Income ($\text{weight} = 0.10$): Linear scale between Rs. 10k and Rs. 40k
- **Academic Highlight:** Missing data handling via **dynamic weight rescaling** (no arbitrary data fabrication).
- **Categories:** Lower ($<35$, Green), Moderate ($35-65$, Yellow), Higher ($\ge 65$, Red).

#### Slide 6: Food-Support Center Management & Dual Registration (Time: 1:30)
- **The Operational Challenge:** Relief workers need fast data entry in the field.
- **Quick Add Workflow:** Enter Name, select Community, enter Phone $\rightarrow$ Done in $<15$ seconds! Inherits community coordinates automatically.
- **Comprehensive 5-Section Registration:**
  - Section A: Profile & Categorization (NGO, Community Kitchen, Food Bank, etc.)
  - Section B: Geospatial Location (Interactive Leaflet point-and-click picker, distance calculation)
  - Section C: Contact Details (Click-to-Call, WhatsApp click-to-chat, Email)
  - Section D: Operations & Schedules (Meal types, operating days/hours, eligibility)
  - Section E: Governance & Verification (Operational status, verification workflow)

#### Slide 7: Geospatial Proximity Engine (Haversine Formula) (Time: 1:00)
- **Mathematical Principle:** Great-circle distance between two points on a sphere.
- **Formula:**
  $$d = 2R \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$
- **Key Advantage:** Instantaneous $\mathcal{O}(1)$ calculation, offline capable, zero external API costs.
- **Real-Time Feedback:** Instant distance-to-community readout in the registration form and details view.

#### Slide 8: Verification, Quality Assurance & Testing (Time: 1:30)
- **Unit Testing:** 38 automated test cases covering models, scoring, database triggers, and API routes.
- **Workflow Verification:** 16-step simulated end-to-end integration test.
- **Security & Integrity:** Parameterized SQL queries preventing SQL injection, Jinja2 auto-escaping preventing XSS, and Foreign Key constraints.

---

### Live Demonstration Plan (5 Minutes)

#### Step 1: Executive Dashboard (`/`) (1 min)
- Showcase live statistics calculated dynamically from the SQLite database.
- Demonstrate vulnerability distribution cards and recent activity tables.

#### Step 2: Interactive GIS Map (`/map`) (1.5 min)
- Showcase the multi-layer map canvas.
- Toggle between **Both Layers**, **Communities Only**, and **Food Centers Only**.
- Filter by vulnerability tier (Higher / Moderate / Lower).
- Click a community marker to show popup with calculated score and direct navigation links.
- Click a food-support center marker to inspect operating hours, contact links, and verification status.

#### Step 3: Fast Food-Support Center Registration (`/centers/add`) (1.5 min)
- Demonstrate **Quick Add Tab**:
  - Type center name: *"Vidya Community Kitchen"*.
  - Pick existing community from dropdown: *"Shanti Nagar"*.
  - Enter phone number: *"+91 98765 43210"*.
  - Submit form $\rightarrow$ Successfully created in seconds!
- Switch to **Full Registration Tab**:
  - Showcase Leaflet map pin placement.
  - Demonstrate live distance recalculation as marker is dragged.
  - Showcase WhatsApp and click-to-call actions.

#### Step 4: Verification & Center Management (`/centers/<id>`) (1 min)
- Open center detail page.
- Test interactive contact links (`tel:`, `https://wa.me/`, `mailto:`).
- Click **Update Status** modal $\rightarrow$ Change status from *Newly Added* to *Verified* with field notes.
- Confirm dashboard statistics update immediately.

---

### Examiner Q&A Defense Strategy
1. **Be confident about academic boundaries:** Emphasize that the system models *relative vulnerability* for decision support; it does not track individual hungry people.
2. **Highlight zero external costs:** Reiterate that Leaflet + OpenStreetMap + SQLite enables any NGO to run this system on zero budget.
3. **Point to automated tests:** Cite the 38 unit tests and 16 workflow tests as proof of software engineering rigor.
