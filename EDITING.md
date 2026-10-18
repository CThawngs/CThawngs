# Cách chỉnh sửa (chỉ cần nhớ 1 file: `profile.json`)

| Muốn đổi | Sửa ở đâu |
|---|---|
| Tên, role, địa chỉ, email, trạng thái | `profile.json` → `person` |
| Link portfolio / LinkedIn / Instagram | `profile.json` → `links` (đổi 1 chỗ, badge + About + mọi nơi dùng đều đổi theo) |
| Kinh nghiệm, học vấn | `experience`, `education` |
| Skills | `skills` (thêm `"show": false` để ẩn một nhóm) |
| Project nổi bật | `projects` |
| Danh sách repo hiển thị | `repos` (chỉ cần tên; mô tả, ngôn ngữ, sao tự lấy từ GitHub mỗi ngày) |
| Chứng chỉ / thành tích | `highlights` |
| Bố cục trang | `README.tpl.md` |

Trong `profile.json` có thể tái sử dụng giá trị bằng biến: `{{person.name}}`, `{{links.portfolio}}`, `{{experience.0.role}}`,
`{{ai_agents|join}}` (nối bằng " · "), `{{ai_agents|join:4}}` (4 phần tử đầu), `{{text|cap}}` (viết hoa chữ đầu).

Sau khi sửa và commit lên `main`, GitHub Actions tự chạy `build.py` và cập nhật `README.md` + `assets/`.
Chạy thử trên máy: `python build.py` (không cần cài gì thêm). **Không sửa tay `README.md` hay `assets/`**, chúng bị ghi đè mỗi lần build.

Heatmap và thẻ repo tự làm mới mỗi ngày. Mô tả repo lấy từ GitHub: muốn đổi thì sửa description của repo (xoá `fallback_description` tương ứng nếu có).
Đổi ảnh chân dung ASCII (tuỳ chọn): xem `tools/make_portrait.py`.
