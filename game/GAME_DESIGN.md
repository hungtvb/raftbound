# RAFTBOUND — Game Design & Roadmap

## 1. Tầm nhìn

Game sinh tồn một người, góc nhìn thứ ba, trên chiếc bè giữa đại dương. Người chơi bắt đầu với chiếc vợt và bè gỗ nhỏ; nhặt vật trôi từ dòng hải lưu, biến đồ bỏ đi thành vật dụng thiết yếu, xây nơi sống nổi và duy trì các hệ thống cung ứng lâu dài. Phong cách hình ảnh: stylized 3D / low-poly có chủ đích, tông biển xanh ngọc, gỗ ấm, HUD hải trình.

## 2. Vòng lặp chính

**Quan sát vật phẩm → quăng vợt → thu gom → chọn công thức → xây thiết bị/mở bè → bảo đảm thức ăn/nước → vượt qua nguy hiểm → khai mở công nghệ cao hơn.**

Các nguồn lực và công dụng trong prototype:

| Tài nguyên | Thu nhận | Công dụng |
|---|---|---|
| Gỗ | Gỗ nổi | Sàn bè, bếp, lọc nước, khay trồng, rương, giáo |
| Nhựa | Chai nhựa | Sàn bè, thiết bị |
| Lá | Lá nổi | Khay trồng |
| Kim loại | Phế liệu | Bếp, lọc nước, giáo |
| Hạt giống | Hộp hạt trôi | Khay trồng |
| Cá sống | Cá nổi, đôi khi vớt ngẫu nhiên | Nấu thành khẩu phần |
| Thức ăn | Bếp nướng/khay trồng | Hồi chỉ số độ no |
| Nước sạch | Máy lọc nước | Hồi chỉ số khát |

## 3. Hệ thống đã lập trình

- **Thế giới:** mặt nước WebGL2 gợn sóng theo thời gian; bè cấu thành từ ô lưới; nhân vật 3D; trang trí bầu trời; cá mập tuần tra.
- **Điều khiển:** WASD, góc nhìn thứ ba bằng chuột phải, thao tác vợt bằng Space/chạm.
- **Thu thập:** vật phẩm mang tốc độ và nhịp nổi riêng, sinh ở mép trước dòng chảy; tự lọc mục tiêu gần nhất trước người chơi; hoạt ảnh quăng lưới và dây.
- **Kinh tế:** kho tám loại vật phẩm, chi phí chế tạo, kiểm tra đủ tài nguyên, công trình chiếm ô sàn.
- **Sản xuất:** thiết bị tự chế nước; bếp tự chuyển cá sống thành thức ăn; khay trồng tự tạo sản lượng.
- **Sinh tồn:** đói, khát, sức khỏe; suy kiệt nếu thiếu ăn/uống; cá mập định kỳ gây sát thương; chế tạo giáo để giảm sát thương.
- **Tiến triển:** sáu nhiệm vụ tuần tự, nhiều ngày sinh tồn.
- **Lưu game:** localStorage, tự động mỗi 10 giây và khi đóng/tab tạm dừng.

## 4. Điểm khác biệt nên phát triển

1. **Hải lưu sống:** xác định hướng dòng chảy, dự báo luồng phế liệu trên bản đồ, thay đổi theo thời tiết.
2. **Thiết kế bè tự do:** đặt sàn theo grid, tường, tầng trên, dây điện, hệ thống ống dẫn và bảo vệ chống sóng.
3. **Thám hiểm:** đảo nhỏ, tàu đắm, vùng phóng xạ/biển sâu, kho báu và nhật ký cốt truyện.
4. **Hệ sinh thái:** câu cá, trồng trọt cần hạt/đất/nước, bắt mưa, máy nấu, phân bón.
5. **Thiên tai:** bão, sét, sóng lớn, độ bền bè; cá mập cắn cấu kiện có thể bị phá hủy.
6. **Technology tree:** mở khóa thiết bị theo nghiên cứu và tài nguyên hiếm.

## 5. Kiến trúc production đề xuất

Prototype hiện tại chủ ý tự dựng WebGL2 để có thể mở `index.html` không cần cài dependency. Để làm game dài hạn, nên chuyển sang Vite + TypeScript + Three.js/Babylon.js, với các lớp chức năng:

- `WorldSystem`: hải lưu, spawn item, thời tiết, chu kỳ ngày/đêm
- `PlayerController`: camera, movement, animation state
- `CollectSystem`: raycast, lực ném, dây vợt, vùng bắt
- `BuildSystem`: grid placement, va chạm, snap, vật liệu
- `Inventory/CraftingSystem`: item data, recipes, unlocks
- `SurvivalSystem`: đói/khát, buff/debuff, damage
- `ProductionSystem`: máy lọc, bếp, nông nghiệp, nhiên liệu
- `AISystem`: trạng thái cá mập (patrol/approach/attack/flee)
- `SaveSystem`: schema versioning, migration, autosave
- `UISystem`: HUD, hotbar, menu chế tạo, hướng dẫn tương tác

Các tài sản 3D nên dùng glTF 2.0, vật liệu PBR mức stylized, kèm LOD và instancing cho tài nguyên nổi. Tiêu chí định lượng cần được test trên thiết bị mục tiêu: FPS/frametime, draw calls, thời gian tải, kích thước asset và lỗi JS/WebGL trong runtime.

## 6. Phạm vi nghiệm thu v0.1

**Có thể kiểm tra:** thao tác WASD, camera, bắt vật phẩm, chi phí chế tạo, mở rộng sàn, tạo đồ ăn/nước, sáu nhiệm vụ, save/load.

**Chưa có/chưa nghiệm thu:** đồ họa được xác nhận trong phiên Chrome thực tế; rigid-body physics; multiplayer; âm thanh; hiệu ứng thời tiết, đảo/tàu, kiếm sống dưới nước; hệ thống độ bền mỗi ô bè; điều khiển đặt công trình bằng ghost preview; gamepad; accessibility đầy đủ; automated end-to-end browser gameplay tests.
