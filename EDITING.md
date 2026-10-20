# Cách chỉnh sửa (chỉ cần nhớ 1 file: `profile.json`)

Trang hiện chỉ gồm: **header → badges → chân dung + thẻ thông tin → Projects (tối đa 6 card) → Contributions → Trophies → footer**.

| Muốn đổi | Sửa ở đâu |
|---|---|
| Tên, role, địa chỉ, email | `profile.json` → `person` |
| Link portfolio / LinkedIn / Instagram / Email | `profile.json` → `links` (đổi 1 chỗ, badge và mọi nơi dùng đều đổi theo) |
| 4 dòng gõ chữ trên header | `profile.json` → `hero.roles` |
| Thông tin trên thẻ bên cạnh chân dung | `profile.json` → `info_card` |
| 6 project nổi bật (tối đa 6) | `profile.json` → `projects` |
| Vibe màu | `profile.json` → `theme` |
| Bố cục trang | `README.tpl.md` |

Trong `profile.json` có thể tái sử dụng giá trị bằng biến: `{{person.name}}`, `{{links.portfolio}}`,
`{{ai_agents|join}}` (nối bằng " · "), `{{ai_agents|join:4}}` (4 phần tử đầu), `{{text|cap}}` (viết hoa chữ đầu).

Các khối dữ liệu `experience`, `education`, `highlights`, `skills`, `repos` vẫn nằm trong `profile.json`
nhưng **hiện không được hiển thị** (đã bỏ section tương ứng). Muốn dùng lại: thêm block tương ứng
vào `README.tpl.md` và khôi phục phần sinh SVG trong `build.py` (xem lịch sử git).

Sau khi sửa và commit lên `main`, GitHub Actions tự chạy `build.py` và cập nhật `README.md` + `assets/`.
Chạy thử trên máy: `python build.py` (không cần cài gì thêm). **Không sửa tay `README.md` hay `assets/`**, chúng bị ghi đè mỗi lần build.

Heatmap tự làm mới mỗi ngày. Đổi ảnh chân dung ASCII (tuỳ chọn): xem `tools/make_portrait.py`.

Link của project: đặt `"url": "https://github.com/owner/repo"` (hoặc `null` = không có repo, card sẽ trỏ về portfolio).
Khi build online, `build.py` kiểm tra từng link GitHub: repo trả **404** (private hoặc đã xoá) sẽ bị cảnh báo và card tự trỏ về
link portfolio — nên không bao giờ có link chết trên README. Muốn bỏ qua kiểm tra: `python build.py --offline`.
