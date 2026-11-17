# Lab Radar — Data format (v2)

Ba file dữ liệu, mỗi file là một mảng JSON:

| File | Nội dung | Ai tạo | Public? |
|---|---|---|---|
| `data/events.json` | Hội nghị, workshop, summer school, special issue | LLM (prompt A/C) + bạn kiểm tra | Có |
| `data/repos.json` | Repo GitHub | `scripts/collect_repos.py` (tự động) | Có |
| `data/jobs.json` | Việc làm & fellowship | LLM (prompt B/C) + bạn kiểm tra | **Không** (bị `.gitignore`) |

Ngoài ra: `data/gold_list.json` (danh sách "phải có" để đo recall), `data/logs/` (log truy vấn và changelog).

## Quy tắc chung (áp dụng cho mọi bản ghi)

- Không biết thì ghi `null`. Không dùng `"N/A"`, `"TBA"`, `"null"` hay `0`.
- Ngày: `YYYY-MM-DD`. Nếu có giờ chốt thì ghi `tz` (IANA, ví dụ `Europe/Berlin`), hoặc ghi `"AoE"`.
- `id` cố định, không đổi giữa các lần cập nhật.
- `sourceDate` là ngày **thực sự** mở trang nguồn ra kiểm tra.
- `verification`:
  - `full`: mọi trường có giá trị đều đã đối chiếu với trang chính thức.
  - `partial`: chỉ một số trường.
  - `lead`: mới thấy ở cổng tổng hợp, chưa kiểm tra.
- Khi hai nguồn chính thức mâu thuẫn: lấy nguồn có ngày đăng mới nhất và ghi vào `conflicts`.
- `subjects`: một hoặc nhiều mã trong `WATER`, `ALGAE`, `AI_ENV`, `ENV_BIOINFO`, `CARBON_PFAS`, `OCEAN`.
- `tier`: `1` (cốt lõi), `2` (lân cận) hoặc `3` (ngoại vi). Định nghĩa trong `scope.json`.
- `region`: `TW`, `VN`, `EAST_ASIA`, `SE_ASIA`, `OCEANIA`, `EUROPE`, `NORDIC`, `NORTH_AMERICA`, `LATIN_AMERICA`, `MEA`, `ONLINE`.
- `country`: mã ISO-3166 alpha-2 hoặc `null`. Các nước DK, SE, NO, FI, IS phải dùng region `NORDIC`.
- Bản dịch: trường tiếng Anh là mặc định. Bản tiếng Việt (nếu có) đặt trong `vi: {"title": ..., "notes": ...}`. Bản dịch **không** được tính là đã kiểm chứng lại.

## events

```json
{
  "id": "evt-isap-2027",
  "kind": "Conference",
  "title": "9th Congress of the International Society for Applied Phycology",
  "acronym": "ISAP 2027",
  "organizer": "ISAP; Murdoch University",
  "subjects": ["ALGAE"],
  "tier": 1,
  "region": "OCEANIA",
  "country": "AU",
  "city": "Perth",
  "mode": "In-person",
  "startDate": "2027-11-21",
  "endDate": "2027-11-26",
  "status": "Announced",
  "milestones": [
    {"type": "abstract", "date": null, "tz": null, "note": "Not announced"}
  ],
  "remotePresentation": null,
  "fee": {"text": null, "value": null, "currency": null, "basis": null},
  "proceedings": {"text": null, "verified": false},
  "urls": ["https://www.appliedphycologysoc.org/Congress-2027"],
  "contact": null,
  "sourceDate": "2026-11-16",
  "verification": "partial",
  "conflicts": [],
  "notes": "",
  "vi": {}
}
```

- `kind`: `Conference`, `Workshop`, `Summer School`, `Special Issue`.
- `mode`: `In-person`, `Hybrid`, `Online`, `Journal`.
- `status`:
  - `Announced`: đã xác nhận có edition, nhưng nộp bài chưa mở hoặc chưa xác minh được trạng thái.
  - `Open`: còn ít nhất một mốc mở.
  - `Closed`: hết hạn nộp bài; có thể vẫn còn đăng ký tham dự.
  - `Watchlist`: chưa công bố edition. Bắt buộc `startDate: null`.
  - `Archived`: đã diễn ra.
  - `Cancelled`.
- `milestones[].type`: `abstract`, `full_paper`, `special_session`, `notification`, `camera_ready`, `early_bird`, `registration`. Hạn nộp bài (`abstract`, `full_paper`, `special_session`) phải tách khỏi hạn đăng ký (`early_bird`, `registration`).
- `fee.value` chỉ là số khi `fee.basis` đã rõ (ví dụ `"regular, non-member, early bird"`). Phí APC của tạp chí **không** phải phí hội nghị.
- `remotePresentation`: `"yes"`, `"no"` hoặc `null`.

## jobs

```json
{
  "id": "job-dtu-2026-1234",
  "title": "Postdoc in ML for wastewater process control",
  "employer": "Technical University of Denmark",
  "unit": "DTU Sustain",
  "postingId": "1234",
  "roleType": "Postdoc",
  "subjects": ["WATER", "AI_ENV"],
  "tier": 1,
  "region": "NORDIC",
  "country": "DK",
  "city": "Kongens Lyngby",
  "mode": "Onsite",
  "status": "Active",
  "deadline": "2026-12-15",
  "tz": "Europe/Copenhagen",
  "start": null,
  "duration": "2 years",
  "salary": {"text": null, "value": null, "currency": null, "period": null, "basis": null},
  "visa": null,
  "requirements": "",
  "urls": [],
  "sourceDate": "2026-11-16",
  "verification": "full",
  "notes": "",
  "vi": {}
}
```

(Ví dụ trên chỉ minh họa định dạng; tin tuyển dụng này không có thật.)

- `roleType`: `Postdoc`, `Research Scientist`, `Assistant Professor`, `Research Engineer`, `Data Scientist`, `Fellowship`, `Other`. Fellowship như MSCA, JSPS, Humboldt cũng ghi vào đây.
- `mode`: `Onsite`, `Hybrid`, `Remote`. Vị trí có công việc wet-lab thì không được ghi `Remote`.
- `status`: `Active`, `Closed`, `Unverified`, `Archived`.
- `salary.value` chỉ là số khi đủ cả `currency`, `period` (`year`, `month` hoặc `hour`) và `basis` (`gross` hoặc `net`).

## repos (tự động sinh, không sửa tay trừ `notes`, `tierOverride`, `exclude`)

| Trường | Ý nghĩa |
|---|---|
| `id` | `gh:<owner>/<name>` |
| `fullName`, `url`, `description`, `topics[]`, `language`, `license` | Lấy từ GitHub |
| `stars`, `forks`, `createdAt`, `pushedAt`, `archived` | Lấy từ GitHub |
| `maintenance` | `active` (có push trong `activeMonths`), `stale` hoặc `archived` |
| `subjects[]`, `tier` | Lấy từ truy vấn khớp có tier ưu tiên nhất. `tierOverride` (do bạn đặt) có quyền cao hơn |
| `matchedQueries[]` | Các truy vấn đã trả về repo này |
| `needsReview` | `true` nếu tên, mô tả và topics không chứa từ nào trong `mustMatchAny`. Khi đó repo chỉ khớp qua README và rất có thể là nhiễu |
| `linkedDOIs[]`, `linkedArxiv[]` | DOI và mã arXiv tìm thấy trong README |
| `citationFile` | `true` nếu repo có `CITATION.cff` |
| `licenseClass` | `permissive` (MIT, Apache, BSD…), `copyleft` (GPL, AGPL, LGPL, MPL…), `other` (giấy phép tùy chỉnh hoặc không nhận diện được) hoặc `none` |
| `reusable` | `true` nếu `licenseClass` là `permissive` hoặc `copyleft`, và repo không bị archived. Dùng cho chế độ xem **Dùng cho lab** |
| `hasPaper`, `paperEvidence[]` | Repo có bằng chứng gắn với một công bố hay không, và bằng chứng nào (CITATION.cff, DOI, arXiv, mô tả). Dùng cho chế độ xem **Trích dẫn trong review** |
| `firstSeen`, `lastSeen`, `sourceDate` | Ngày hệ thống ghi nhận |
| `exclude` | `true` để ẩn vĩnh viễn (do bạn đặt) |

## gold_list.json

```json
{"events": ["evt-isap-2027"], "repos": ["gh:owner/name"], "jobs": []}
```

`validate.py` báo trong số các ID này có bao nhiêu đã xuất hiện trong dữ liệu. Đó là chỉ số recall tối thiểu của công cụ.
