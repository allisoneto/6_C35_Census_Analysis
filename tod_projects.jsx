import { useState } from "react";

const projects = [
  {
    year: 2012,
    name: "Wonderland Intermodal Transit Center",
    location: "Revere, MA — Blue Line (Wonderland)",
    type: "Transit Infrastructure + TOD Catalyst",
    developer: "MBTA",
    size: "$53.5M; 1,465-space parking garage + sheltered busway",
    description:
      "A $53.5M reconstruction of Wonderland Station funded partly by the 2009 American Recovery and Reinvestment Act. The project added a major parking garage, a covered busway, bicycle storage, a pedestrian bridge over Ocean Avenue to Revere Beach, and improved North Shore bus connections. It served as the anchor catalyst for adjacent private transit-oriented development along the Blue Line corridor.",
    transit: "Blue Line",
    color: "#0055A4",
  },
  {
    year: 2014,
    name: "Assembly Station & Assembly Row Phase 1",
    location: "Somerville, MA — Orange Line (Assembly)",
    type: "Mixed-Use TOD",
    developer: "Federal Realty Investment Trust + MBTA",
    size: "45-acre brownfield; new Orange Line station; 323,000 SF retail",
    description:
      "The first new MBTA subway station since 1987, opened September 2, 2014, built by Federal Realty on the former Ford Motor Company assembly plant where the ill-fated Edsel was built. Phase 1 included 323,000 SF of outlet and retail space, a riverfront park, and the dedicated Orange Line stop, with developer contributions helping fund the station itself.",
    transit: "Orange Line",
    color: "#E87722",
  },
  {
    year: 2015,
    name: "Ink Block Phase 1",
    location: "South End, Boston — Silver Line / Bus",
    type: "Mixed-Use TOD",
    developer: "National Development",
    size: "315 apartments (1 Ink, 2 Ink, 3 Ink); Sepia condos; 50,000 SF Whole Foods",
    description:
      "Phase 1 of the redevelopment of the former Boston Herald printing plant at 300 Harrison Ave in the South End's New York Streets neighborhood. Three apartment towers and the Sepia condominium building debuted alongside a flagship Whole Foods and 32,000 SF of street-level retail. The project revitalized a long-underused industrial block within easy reach of Silver Line and multiple MBTA bus routes.",
    transit: "Silver Line / Bus",
    color: "#7B2D8B",
  },
  {
    year: 2017,
    name: "Assembly Row Phase 2",
    location: "Somerville, MA — Orange Line (Assembly)",
    type: "Mixed-Use TOD",
    developer: "Federal Realty Investment Trust",
    size: "447-unit Montaje tower; 122-unit Alloy condos; 158-key Marriott hotel; expanded retail",
    description:
      "Phase 2 added the 20-story Montaje apartment tower, the Alloy condominium building atop a boutique Marriott Autograph Collection hotel, and expanded the retail/restaurant roster to over 100 tenants. Partners HealthCare (now Mass General Brigham) signed a massive 825,000 SF, 13-story office headquarters at Assembly Row, legitimizing the district as a major employment destination.",
    transit: "Orange Line",
    color: "#E87722",
  },
  {
    year: 2018,
    name: "Ink Block Phase 3 (AC Hotel + Siena Condos)",
    location: "South End, Boston — Silver Line / Bus",
    type: "Mixed-Use TOD",
    developer: "National Development",
    size: "206-key AC Hotel by Marriott + 76 condominium units at Siena",
    description:
      "Phase 3 of Ink Block completed the eastern portion of the site with a 206-room AC Hotel by Marriott and 76 condominiums in the Siena building. The broader Ink Block campus became one of Boston's most successful urban infill TOD projects, bringing over 1,000 residents, a hotel, and significant retail to a transit-accessible former industrial site.",
    transit: "Silver Line / Bus",
    color: "#7B2D8B",
  },
  {
    year: 2018,
    name: "345 Harrison Avenue",
    location: "South End, Boston — Silver Line / Bus",
    type: "Residential + Retail TOD",
    developer: "National Development",
    size: "Two 14-story towers; 585 luxury apartments; 40,000 SF ground-floor retail",
    description:
      "Dual residential towers directly across Harrison Avenue from Ink Block, with 585 apartments and 40,000 SF of street-level retail. The development includes extensive bicycle infrastructure and Bluebikes docking stations, and sits within steps of multiple MBTA bus routes and Silver Line rapid transit stops — cementing the New York Streets area as one of Boston's densest transit-oriented residential nodes.",
    transit: "Silver Line / Bus",
    color: "#7B2D8B",
  },
  {
    year: 2019,
    name: "A.O. Flats at Forest Hills",
    location: "Jamaica Plain, Boston — Orange Line (Forest Hills)",
    type: "Affordable TOD",
    developer: "The Community Builders (TCB)",
    size: "78 units (100% affordable/mixed-income); 1,500 SF retail; LEED Platinum",
    description:
      "A 78-unit affordable mixed-income community built on a formerly vacant MBTA parcel in Jamaica Plain, steps from the Forest Hills Orange Line and commuter rail station. The five-story LEED Platinum-certified building includes ground-floor retail, a pocket park, and bicycle storage. Grand opening was held in September 2019 with Mayor Walsh. The project is cited as a flagship example of how MBTA surplus parcels can deliver affordable transit-adjacent housing.",
    transit: "Orange Line",
    color: "#E87722",
  },
  {
    year: 2019,
    name: "Bartlett Station Phase 1 (Buildings B + Condos)",
    location: "Roxbury (Nubian Square), Boston — Orange Line / Bus",
    type: "Affordable Mixed-Use TOD",
    developer: "Nuestra Comunidad Development Corp. + Windale Developers",
    size: "60 mixed-income rental units + 16 condominiums; 13,300 SF retail; 8-acre brownfield",
    description:
      "Phase 1 of a five-phase redevelopment of the former MBTA Bartlett Bus Yard in Nubian Square. Completed August 2019, the first two buildings delivered 60 affordable rental apartments (Building B) and 16 for-sale condominiums on the 8-acre contaminated brownfield. Two-thirds of units are affordable. The full project envisions ~380 homes, 54,000 SF of commercial space, and the Oasis @ Bartlett public arts plaza. Ribbon cutting was on August 15, 2019.",
    transit: "Orange Line / Bus",
    color: "#E87722",
  },
  {
    year: 2020,
    name: "Bower at Fenway Center (Phase 1)",
    location: "Fenway, Boston — Green Line (Kenmore/Fenway) / Commuter Rail",
    type: "Residential TOD over Mass Pike Air Rights",
    developer: "Gerding Edlen + Meredith Management + Nuveen Real Estate",
    size: "312 units (8-story mid-rise + 14-story tower); $136.6M construction loan",
    description:
      "The first completed phase of the Fenway Center transit-oriented development, built over the Massachusetts Turnpike on a 90,000 SF air rights deck — the largest such structure built in Boston in over four decades. The Bower complex includes an eight-story mid-rise and a 14-story tower with 312 residential units, directly adjacent to the Fenway commuter rail stop and Green Line stations. The broader Fenway Center campus, now led by IQHQ, is being developed into nearly 1 million SF of life science space.",
    transit: "Green Line / Commuter Rail",
    color: "#008150",
  },
  {
    year: 2022,
    name: "Bartlett Station Building A (Phase 1 Completion)",
    location: "Roxbury (Nubian Square), Boston — Orange Line / Bus",
    type: "Affordable Mixed-Use TOD",
    developer: "Nuestra Comunidad Development Corp. + Windale Developers",
    size: "60 mixed-income rental apartments + 12,000 SF commercial; completed Nov. 2022",
    description:
      "Construction commenced March 2021 and completed November 2022. Building A added 60 more mixed-income rental homes and 12,000 SF of commercial space to the Bartlett Station campus, completing Phase 1's full apartment component. MassHousing, DHCD, and the City of Boston co-funded the project. The Oasis @ Bartlett public arts plaza — the centerpiece of the site — features art installations, gardens, and performance space honoring Roxbury's multicultural heritage.",
    transit: "Orange Line / Bus",
    color: "#E87722",
  },
  {
    year: 2022,
    name: "25 Amory Street (Jackson Square Redevelopment)",
    location: "Jamaica Plain, Boston — Orange Line (Jackson Square)",
    type: "Affordable TOD",
    developer: "JPNDC (Jamaica Plain Neighborhood Development Corp.)",
    size: "44 apartments, 100% affordable; completed January 2022",
    description:
      "The first completed building of the new phase of Jackson Square's long-running redevelopment, celebrating its ribbon cutting on June 1, 2022. The 44 fully affordable apartments are on land long vacant after being cleared for a proposed I-95 extension that was never built — parcels that sat empty for up to five decades. By 2022, Jackson Square had delivered 487 new affordable homes over 12 years of redevelopment adjacent to the Orange Line.",
    transit: "Orange Line",
    color: "#E87722",
  },
  {
    year: 2022,
    name: "Green Line Extension (GLX) — Union Square Branch",
    location: "Somerville, MA — Green Line (New Union Square Station)",
    type: "Transit Infrastructure + TOD Catalyst",
    developer: "MBTA / GLX Constructors (design-build)",
    size: "$2.28B total project; 7 new stations; 4.3-mile extension",
    description:
      "The Union Square Branch of the $2.28 billion Green Line Extension opened March 21, 2022 — the first new Green Line branch since 1987. A rebuilt Lechmere Station in Cambridge (elevated) and the new Union Square terminal in Somerville launched service simultaneously. The Medford Branch (5 additional stations to Medford/Tufts) opened December 12, 2022. The GLX increased the share of Somerville residents living within 0.5 mile of rapid transit from 20% to 80%, and has catalyzed extensive TOD construction in Union Square and along the corridor.",
    transit: "Green Line",
    color: "#008150",
  },
  {
    year: 2022,
    name: "Assembly Row Phase 3",
    location: "Somerville, MA — Orange Line (Assembly)",
    type: "Mixed-Use TOD",
    developer: "Federal Realty Investment Trust",
    size: "500-unit Miscela apartments; 277,000 SF office (incl. PUMA HQ); 56,000 SF retail; $465–485M",
    description:
      "Phase 3 completed the core buildout of Assembly Row, adding the 500-unit Miscela luxury residential tower, a 277,000 SF LEED-certified office building (home to PUMA North America's HQ with 450 employees, opened 2021), and 56,000 SF of new street-level retail. Assembly Row won the 2022 CoStar Impact Award for best commercial development in Boston. With all three phases complete, the site holds 1.5M SF of office, 1,400+ apartments, a hotel, and over 500,000 SF of retail.",
    transit: "Orange Line",
    color: "#E87722",
  },
  {
    year: 2023,
    name: "The Loop at Mattapan Station",
    location: "Mattapan Square, Boston — Mattapan Trolley / Commuter Rail",
    type: "Affordable Mixed-Use TOD",
    developer: "Preservation of Affordable Housing (POAH) + Nuestra Comunidad",
    size: "135 affordable rental units; 10,000 SF retail (Daily Table grocery); passive house certified; $57M",
    description:
      "Grand opening celebrated April 25, 2023, with Mayor Wu and Lt. Governor Driscoll. Built on a vacant MBTA parking lot adjacent to the Mattapan Trolley stop and a block from the Mattapan Commuter Rail Station, the six-story passive house-certified building offers 135 affordable apartments across a range of incomes. Nearly half of units are affordable to households at or below 50% AMI. Ground-floor Daily Table nonprofit grocery serves the community at below-market food prices. Features a basketball court, roof deck, gym, and E-bike station.",
    transit: "Mattapan Trolley / Commuter Rail",
    color: "#DA291C",
  },
  {
    year: 2024,
    name: "Allston Yards Building A (Alder + Stop & Shop)",
    location: "Allston, Boston — Boston Landing Commuter Rail",
    type: "Mixed-Use TOD",
    developer: "New England Development + Bozzuto + Stop & Shop",
    size: "165 rental units (Alder by Bozzuto); urban flagship Stop & Shop; 1-acre community green",
    description:
      "The first phase of a 1.4 million SF mixed-use development on the site of a former suburban Stop & Shop, adjacent to the Boston Landing commuter rail stop in Allston. Building A delivered 165 apartments and an urban prototype Stop & Shop grocery store. The Rita Hester Community Green — a one-acre public park named for a beloved local transgender resident — opened June 30, 2024. Future phases will add over 700 more units, 350,000 SF of office/lab space, and 117,000 SF of retail. The project is managed by VHB and required complex coordination with MassDOT, MBTA, and the City.",
    transit: "Commuter Rail (Boston Landing)",
    color: "#80276C",
  },
];

const lineColors = {
  "Blue Line": "#0055A4",
  "Orange Line": "#E87722",
  "Silver Line / Bus": "#7B2D8B",
  "Green Line / Commuter Rail": "#008150",
  "Mattapan Trolley / Commuter Rail": "#DA291C",
  "Commuter Rail (Boston Landing)": "#80276C",
};

const badgeColor = (transit) => {
  if (transit.includes("Blue")) return "#0055A4";
  if (transit.includes("Orange")) return "#E87722";
  if (transit.includes("Silver")) return "#7B2D8B";
  if (transit.includes("Green")) return "#008150";
  if (transit.includes("Mattapan") || transit.includes("Red")) return "#DA291C";
  if (transit.includes("Commuter Rail")) return "#80276C";
  return "#666";
};

export default function BostonTODTimeline() {
  const [selected, setSelected] = useState(null);

  return (
    <div
      style={{
        fontFamily: "'Georgia', serif",
        background: "#0d1117",
        minHeight: "100vh",
        color: "#e8e0d0",
        padding: "48px 28px",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Sans+3:wght@300;400;600&display=swap');
        * { box-sizing: border-box; }
        .tod-card { cursor: pointer; transition: transform 0.18s ease, box-shadow 0.18s ease; }
        .tod-card:hover { transform: translateX(5px); box-shadow: -3px 0 0 #c8a96e; }
        .tod-card.selected { transform: translateX(7px); }
        .detail-panel { animation: slideIn 0.22s ease; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .yr-label { transition: color 0.18s; }
        .expand-arrow { transition: transform 0.2s, color 0.2s; }
      `}</style>

      <div style={{ maxWidth: 880, margin: "0 auto 52px" }}>
        <div style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 11, letterSpacing: "0.2em", textTransform: "uppercase", color: "#c8a96e", marginBottom: 14 }}>
          Metropolitan Boston · MBTA Corridors
        </div>
        <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: "clamp(30px, 5vw, 50px)", fontWeight: 700, margin: "0 0 14px", lineHeight: 1.1, color: "#f0e8d8" }}>
          Transit-Oriented Development
          <br />
          <em style={{ fontStyle: "italic", fontWeight: 400, color: "#c8a96e", fontSize: "0.78em" }}>Boston Area · Completed 2012–2024</em>
        </h1>
        <p style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 15, color: "#7a7068", maxWidth: 560, lineHeight: 1.65, margin: "0 0 24px" }}>
          Major MBTA-adjacent developments combining housing, retail, transit access, and public space — from industrial brownfields to walkable urban neighborhoods. Click any entry to expand.
        </p>
        <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
          {[
            { label: "Blue Line", color: "#0055A4" },
            { label: "Orange Line", color: "#E87722" },
            { label: "Green Line", color: "#008150" },
            { label: "Silver Line / Bus", color: "#7B2D8B" },
            { label: "Mattapan Trolley", color: "#DA291C" },
            { label: "Commuter Rail", color: "#80276C" },
          ].map(({ label, color }) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 7, fontFamily: "'Source Sans 3', sans-serif", fontSize: 12, color: "#7a7068" }}>
              <div style={{ width: 11, height: 11, borderRadius: "50%", background: color }} />
              {label}
            </div>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 880, margin: "0 auto", position: "relative" }}>
        <div style={{ position: "absolute", left: 72, top: 0, bottom: 0, width: 1, background: "linear-gradient(to bottom, transparent, #2e2820 60px, #2e2820 calc(100% - 60px), transparent)" }} />

        {projects.map((p, i) => {
          const bc = badgeColor(p.transit);
          const isSelected = selected === i;
          return (
            <div key={i} style={{ marginBottom: 4 }}>
              <div className={`tod-card ${isSelected ? "selected" : ""}`} onClick={() => setSelected(isSelected ? null : i)} style={{ display: "flex", gap: 28, alignItems: "flex-start", padding: "18px 0" }}>
                <div className="yr-label" style={{ width: 58, flexShrink: 0, textAlign: "right", fontFamily: "'Playfair Display', serif", fontSize: 19, fontWeight: 700, color: isSelected ? "#c8a96e" : "#4a4238", paddingTop: 2 }}>
                  {p.year}
                </div>
                <div style={{ position: "relative", width: 28, flexShrink: 0, display: "flex", justifyContent: "center", paddingTop: 7 }}>
                  <div style={{ width: isSelected ? 13 : 9, height: isSelected ? 13 : 9, borderRadius: "50%", background: bc, boxShadow: isSelected ? `0 0 10px ${bc}99` : "none", transition: "all 0.2s", marginTop: 1 }} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap", marginBottom: 5 }}>
                    <span style={{ display: "inline-block", fontFamily: "'Source Sans 3', sans-serif", fontSize: 10, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", padding: "2px 9px", borderRadius: 2, background: bc + "22", color: bc, border: `1px solid ${bc}44` }}>
                      {p.transit}
                    </span>
                    <span style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 10, color: "#4a4238", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                      {p.type}
                    </span>
                  </div>
                  <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 19, fontWeight: 700, color: isSelected ? "#f0e8d8" : "#c0a878", margin: "0 0 3px", transition: "color 0.18s" }}>
                    {p.name}
                  </h2>
                  <div style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 12, color: "#5a5248" }}>
                    {p.location}
                  </div>
                </div>
                <div className="expand-arrow" style={{ color: isSelected ? "#c8a96e" : "#2e2820", fontSize: 16, paddingTop: 7, transform: isSelected ? "rotate(90deg)" : "none" }}>▶</div>
              </div>

              {isSelected && (
                <div className="detail-panel" style={{ marginLeft: 118, marginBottom: 14, background: "#121820", border: `1px solid ${bc}33`, borderLeft: `3px solid ${bc}`, borderRadius: "0 8px 8px 0", padding: "22px 26px" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px 28px", marginBottom: 18 }}>
                    <div>
                      <div style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "#4a4238", marginBottom: 3 }}>Developer</div>
                      <div style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 13, color: "#c0a878", fontWeight: 600 }}>{p.developer}</div>
                    </div>
                    <div>
                      <div style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "#4a4238", marginBottom: 3 }}>Scale</div>
                      <div style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 13, color: "#c0a878" }}>{p.size}</div>
                    </div>
                  </div>
                  <p style={{ fontFamily: "'Source Sans 3', sans-serif", fontSize: 14, lineHeight: 1.75, color: "#8a8070", margin: 0 }}>{p.description}</p>
                </div>
              )}

              {i < projects.length - 1 && (
                <div style={{ marginLeft: 118, height: 1, background: "#171d24" }} />
              )}
            </div>
          );
        })}
      </div>

      <div style={{ maxWidth: 880, margin: "44px auto 0", paddingTop: 22, borderTop: "1px solid #1a2028", fontFamily: "'Source Sans 3', sans-serif", fontSize: 11, color: "#2e2820" }}>
        Sources: MBTA Realty, MassHousing, Boston.gov, Federal Realty Investment Trust, National Development, POAH, JPNDC, Nuestra CDC, Cranshaw Construction, Commercial Property Executive, Boston Globe
      </div>
    </div>
  );
}