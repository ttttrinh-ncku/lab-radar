# Lab Radar — AI × Environmental Biotechnology

Trang tìm kiếm hội thảo, việc làm và repo học thuật cho hướng nghiên cứu AI × vi tảo × xử lý nước thải (NCKU, Gojobori Lab). Phạm vi gồm Đài Loan, Việt Nam, châu Á – Thái Bình Dương, châu Âu, Bắc Âu, Bắc Mỹ, Mỹ Latinh và các sự kiện trực tuyến.

## Kiến trúc

| Phần | Cách lấy dữ liệu | Tự động? | Công khai? |
|---|---|---|---|
| Repo | `scripts/collect_repos.py` gọi GitHub Search API theo truy vấn trong `scope.json` | Có, GitHub Actions chạy thứ Sáu 08:00 giờ Đài Loan | Có |
| Hội nghị | Prompt A/C trong `prompts/PROMPTS_VI.md`, sau đó bạn kiểm tra | Bán tự động | Có |
| Việc làm | Prompt B/C | Bán tự động | **Không** (`data/jobs.json` nằm trong `.gitignore`) |

`scripts/validate.py` chặn dữ liệu sai schema, ví dụ null giả, ngày sai định dạng, quốc gia Bắc Âu bị gán vùng sai, hay lương thiếu đơn vị. Script cũng báo recall so với `data/gold_list.json`.

`scripts/build.py` tạo hai trang:
- `site/index.html`: bản công khai, không có việc làm.
- `private/report_full.html`: bản đầy đủ, có việc làm, chỉ để trên máy bạn.

Cả hai đều là file độc lập, mở bằng double-click được, không cần server hay thư viện ngoài.

## Cài đặt lần đầu (khoảng 20 phút)

1. **Tạo repo GitHub public**, ví dụ `lab-radar`. Pages miễn phí yêu cầu repo public.
2. **Upload toàn bộ thư mục này** lên nhánh `main`, kể cả thư mục ẩn `.github/`. Nếu kéo-thả trên web làm mất `.github/`, dùng GitHub Desktop hoặc:
   ```bash
   git init && git add . && git commit -m "init" && git branch -M main
   git remote add origin https://github.com/<user>/lab-radar.git && git push -u origin main
   ```
3. **Bật Pages bằng Actions**: vào Settings → Pages → Source, chọn **GitHub Actions** (không chọn "Deploy from a branch").
4. **Cho Actions quyền ghi**: vào Settings → Actions → General → Workflow permissions, chọn **Read and write permissions**.
5. **Chạy lần đầu**: vào tab Actions → `weekly-update` → **Run workflow**. Khoảng 5–10 phút sau, trang có tại `https://<user>.github.io/lab-radar/`.

## Đặt địa chỉ web có tên bạn

Địa chỉ GitHub Pages có dạng `https://<tên-tài-khoản>.github.io/<tên-repo>/`. Địa chỉ web không dùng được dấu tiếng Việt, nên viết không dấu.

| Cách | Địa chỉ ví dụ | Chi phí |
|---|---|---|
| Repo tên `lab-radar` trong tài khoản `ttttrinh-ncku` | `https://ttttrinh-ncku.github.io/lab-radar/` | Miễn phí |
| Repo tên đúng bằng `ttttrinh-ncku.github.io` | `https://ttttrinh-ncku.github.io/` | Miễn phí |
| Mua tên miền riêng | `https://tutrinhtruong.com` | Khoảng 10–20 USD/năm |

Nếu dùng tên miền riêng: mua ở một nhà đăng ký tên miền, tạo bản ghi DNS theo hướng dẫn của GitHub, rồi nhập tên miền vào Settings → Pages → Custom domain và tích "Enforce HTTPS". Repo này deploy bằng Actions, nên không cần file `CNAME`.

Tiêu đề trang lấy từ trường `siteTitle` trong `scope.json`.

## Quy trình hằng tuần

1. Actions tự cập nhật repo vào thứ Sáu. Đọc `data/logs/repos-YYYY-MM-DD.md` để xem repo mới.
2. Chạy prompt C với `data/events.json`, lưu kết quả, rồi chạy:
   ```bash
   python scripts/validate.py      # sửa hết ERROR
   python scripts/build.py
   git add data/events.json && git commit -m "events update" && git push   # push sẽ tự deploy
   ```
3. Việc làm: chạy prompt C với `data/jobs.json` trên máy, rồi build và mở `private/report_full.html`. **Không commit file jobs.**

## Hai chế độ xem trong tab Repo

| Chế độ | Tiêu chí lọc | Sắp xếp | Bước bạn vẫn phải tự làm |
|---|---|---|---|
| **Dùng cho lab** | Có giấy phép kiểu OSI, không bị archived, tầng 1–2 | Theo tầng, rồi mới cập nhật nhất | Clone về và chạy thử. Có giấy phép chỉ có nghĩa là *được phép* dùng, không có nghĩa là code *chạy được*. Với GPL/AGPL: nếu phần mềm của lab dùng code này và được phân phối ra ngoài, nó phải công bố theo cùng giấy phép. |
| **Trích dẫn trong review** | Có CITATION.cff, DOI hoặc arXiv trong README, hoặc mô tả có nhắc tới công bố | Theo tầng, rồi theo số sao | Mở repo và xác nhận đúng bài báo trước khi trích dẫn. Bằng chứng chỉ từ mô tả là yếu. |

## Chỉnh sửa thường gặp

- **Thêm hoặc bớt truy vấn repo**: sửa `repoSearch.queries` trong `scope.json`. `mustMatchAny` là regex chặn nhiễu (ví dụ `pfas\b` để không khớp với `pfast`).
- **Ẩn một repo nhiễu**: trong `data/repos.json`, thêm `"exclude": true` vào repo đó. Collector không ghi đè trường này. Các trường `notes` và `tierOverride` cũng vậy.
- **Đo recall**: thêm vào `data/gold_list.json` khoảng 5–10 ID mà bạn biết chắc phải có.
- **Thêm vùng hoặc chủ đề**: sửa `scope.json`. Trang web và validator đọc trực tiếp từ đó.

## Giới hạn đã biết (cần nhớ)

- Hội nghị và việc làm vẫn phụ thuộc vào chất lượng tìm kiếm của LLM. Search log trong mỗi lần chạy là thứ cho bạn biết đã tìm ở đâu. Đừng tin một lần chạy nào là đầy đủ.
- GitHub Search trả tối đa 1000 kết quả mỗi truy vấn và xếp theo "best match", nên các truy vấn rộng (ví dụ `eDNA metabarcoding`) bị cắt ở `pagesPerQuery × perPage`. `data/logs/repo_queries.csv` ghi lại `total_count` để bạn biết tỷ lệ bị cắt.
- Tìm DOI trong README chỉ chạy tối đa `readmeDoiCheckLimit` repo mỗi lần, ưu tiên repo mới.
- GitHub có thể tạm tắt workflow theo lịch khi repo không có hoạt động trong thời gian dài. Vì bot commit hằng tuần nên trường hợp này khó xảy ra, nhưng thỉnh thoảng hãy mở tab Actions để kiểm tra.
