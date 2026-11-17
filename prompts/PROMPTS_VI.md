# Lab Radar — Bộ prompt (hội nghị, việc làm, cập nhật tuần)

Repo GitHub được thu thập **tự động** bằng `scripts/collect_repos.py`. Các prompt dưới đây chỉ dùng cho hội nghị và việc làm, vì hai loại này không có API.

**Cách dùng:**
1. Mỗi lần chạy, dán **P0** và **một** prompt con. Không gộp nhiều vùng vào một lần chạy: gộp lại thì vùng nào cũng chỉ được tìm sơ sài.
2. Đính kèm `scope.json`, `schema/DATA_FORMAT.md` và file dữ liệu hiện tại (`data/events.json` hoặc `data/jobs.json`).
3. Nhận JSON, lưu vào `data/`, rồi chạy `python scripts/validate.py`. Hết ERROR mới build.

---

## P0 — Quy tắc chung (dán trước mọi prompt)

```text
You are a meticulous research assistant building a verified dataset for a postdoc in Taiwan
working on AI × environmental biotechnology: AI/ML for microalgae photobioreactors and
wastewater bioreactors, digital twins, AIoT, carbon capture, PFAS remediation,
environmental bioinformatics/metagenomics, smart ocean/eDNA.

Attached: scope.json (subjects, tiers, regions, source leads), DATA_FORMAT.md (schema), current data file.

Hard rules:
1. Use live web search. Verify every record on the organizer's/employer's OWN page. Portals,
   aggregators, WikiCFP-type lists and social posts are LEADS only → verification:"lead".
2. Unknown = null. Never "TBA", "N/A", or 0. A fee of 0 only with an explicit "free" statement.
3. Window: today → +18 months (rolling). Include an event outside it only if a submission
   milestone falls inside it.
4. Recurring events with no announced edition → status "Watchlist", startDate null, NO inferred dates.
5. Two official sources disagree → use the most recently dated one; record both in "conflicts".
6. Keep submission milestones (abstract/full_paper/special_session) separate from
   registration milestones (early_bird/registration). Give tz (IANA or "AoE") whenever a cut-off time exists.
7. Assign subjects (multi-label) and tier exactly per scope.json definitions. Tier 1 requires
   BOTH an AI/data/control component AND an algae/wastewater/bioreactor component.
8. Nordic countries (DK, SE, NO, FI, IS) use region "NORDIC"; other European countries "EUROPE".
9. Keep existing ids stable. Never delete a record: change status (Closed/Archived/Cancelled).
10. ACRONYM COLLISIONS: many conferences share acronyms across fields (e.g., "ISAP" = Int. Society
    for Applied Phycology AND Int. Symposium on Antennas and Propagation). Before accepting any
    page — especially a "<acronym><year>.org" domain — confirm the organizer and scope match.
    Also actively look for a dedicated congress site (search "<full name> <year>" and
    "<acronym> <year> <city>"), not only the society page. Record rejected look-alikes in notes.
11. Output: (a) ONE complete JSON array for the file, valid against DATA_FORMAT.md;
    (b) a search log table: query | engine/site | date | #hits | #kept;
    (c) a change log: added / changed (old→new) / archived / could-not-verify (with reason).
    Report blocked pages as blocked; a blocked page is not evidence that a call is closed.
Time zone for "today": Asia/Taipei.
```

---

## A — Hội nghị, workshop, summer school (chạy lần lượt A1 → A4)

```text
TASK A{n}: Find conferences, workshops and summer schools for region group: {GROUP}.
Search systematically using (i) the sourceLeads in scope.json for these regions, (ii) the
keyword grid below combined with "conference 2027", "call for abstracts", "symposium",
"summer school", and site-restricted queries listed for the group.

Keyword grid (combine one from each row where sensible):
- domain: microalgae | algae biotechnology | photobioreactor | wastewater treatment |
  activated sludge | membrane bioreactor | anaerobic digestion | water reuse | PFAS |
  carbon capture | environmental metagenomics | eDNA | harmful algal bloom
- method: machine learning | artificial intelligence | digital twin | soft sensor |
  process control | modelling | IoT | automation

Also check these known series for a current edition: ISAP congress, AlgaEurope (EABA),
Algae Biomass Summit (ABO), IWA World Water Congress, IWA specialist conferences
(Watermatex, ICA, Leading-Edge Technologies, Microbial Ecology & Water Engineering),
WEFTEC, Climate Change AI workshops at NeurIPS/ICML/ICLR, ISMB (ISCB), ISME.
Return records for events in this region group only; online events go to A4.
```

| Lần chạy | {GROUP} | Truy vấn giới hạn site gợi ý |
|---|---|---|
| A1 | `TW, VN, EAST_ASIA, SE_ASIA, OCEANIA` | `site:edu.tw`, `site:gov.tw`, `site:edu.vn`, `site:ac.jp`, `site:ac.kr`, `site:edu.au`, `site:edu.sg` |
| A2 | `EUROPE, NORDIC` | `site:dk`, `site:se`, `site:no`, `site:fi`, `site:nl`, `site:de`, `site:ch`, `site:ac.uk`, `site:eu` |
| A3 | `NORTH_AMERICA, LATIN_AMERICA` | `site:edu`, `site:gov`, `site:ca`, `site:br`, `site:mx`, `site:cl` |
| A4 | `ONLINE` (cả hybrid toàn cầu) + workshop AI | `climatechange.ai`, `openreview.net` (chỉ để tìm workshop; xác minh trên trang workshop) |

**A-SI (tùy chọn): Special issue phục vụ bài review.**

```text
TASK A-SI: Find OPEN special issues / article collections (deadline within 12 months)
relevant to AI for algae or wastewater bioprocesses in: Water Research, Water Research X,
Bioresource Technology, Algal Research, Chemical Engineering Journal, Journal of Environmental
Management, Environmental Science & Technology, npj Clean Water, Science of the Total Environment.
kind:"Special Issue", mode:"Journal". Record APC separately in notes; it is NOT a conference fee.
Verify on the journal's own page; record guest editors and the manuscript deadline.
```

---

## B — Việc làm & fellowship (B1 → B3)

```text
TASK B{n}: Find open positions and fellowships for region group: {GROUP}.
Roles: Postdoc, Research Scientist, Assistant Professor, Research Engineer, Data Scientist,
Fellowship (e.g., MSCA Postdoctoral Fellowships, Humboldt, JSPS, NSTC, Mitacs, FAPESP).
Candidate profile: PhD; AI/ML + environmental biotechnology/microalgae/wastewater; based in Taiwan;
Vietnamese citizen → ALWAYS record visa/sponsorship and nationality/eligibility restrictions.
Exclude clinical roles. Wet-lab duties ⇒ never mode "Remote".
Use scope.json sourceLeads.jobs for the group plus targeted queries
("postdoc wastewater machine learning", "postdoc microalgae", "digital twin water postdoc",
"PFAS postdoc", "environmental bioinformatics postdoc").
Deduplicate by employer + postingId, or canonical URL. Salary numeric only with currency, period, gross/net.
```

| Lần chạy | {GROUP} | Gợi ý thêm |
|---|---|---|
| B1 | `EUROPE, NORDIC` | EURAXESS, Jobbnorge (Na Uy), cổng tuyển dụng của DTU/KTH/Chalmers/Lund/Uppsala/NTNU/Aalto/Helsinki, Eawag, Wetsus, KWR, jobs.ac.uk, AcademicTransfer |
| B2 | `NORTH_AMERICA, LATIN_AMERICA` | Science Careers, Nature Careers, HigherEdJobs, PNNL, Water Research Foundation, Mitacs/NSERC, FAPESP |
| B3 | `TW, VN, EAST_ASIA, SE_ASIA, OCEANIA` | NSTC, NCKU, Academia Sinica, JREC-IN (Nhật), JSPS, NRF (Hàn), A*STAR/NUS/NTU, CSIRO, Murdoch |

---

## C — Cập nhật hằng tuần (thứ Sáu, Asia/Taipei)

```text
TASK C: Weekly re-verification of the attached data file.
1. Re-open the official URL of EVERY existing record before adding anything new.
   Update changed fields and sourceDate; record old→new in the change log.
2. Status transitions: events past endDate → Archived; submission closed → Closed (registration
   may remain open — keep those milestones); jobs past deadline → Closed; unreachable source →
   keep the record, status Unverified (jobs) / leave unchanged with a note (events).
3. Then run a short new-item sweep: the 5 highest-yield queries from the last search log for
   each region group.
4. Flag all submission/application deadlines within 30 days at the top of the change log.
5. A new translation does not count as re-verification.
Output the full JSON array, search log, and change log (P0 rule 10).
```

Sau khi nhận kết quả, chạy `python scripts/validate.py && python scripts/build.py`, rồi commit (xem README).
