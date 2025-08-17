# Giải quyết vấn đề ảnh không hiển thị sau khi build

## Vấn đề
Khi chạy `npm run build`, các ảnh từ folder `asset/` không hiển thị được sau khi deploy.

## Nguyên nhân
1. **Folder `asset/` nằm ở thư mục gốc** nhưng **Vite chỉ copy thư mục `public/`** vào `dist/` khi build
2. **Cấu hình Vite**: `publicDir: 'public'` trong `vite.config.ts`
3. **Kết quả**: Các ảnh từ `asset/` không được copy vào `dist/`, nên khi deploy sẽ không hiển thị được

## Giải pháp đã áp dụng

### 1. Di chuyển folder `asset/` vào `public/`
```bash
mv asset public/
```

### 2. Thay đổi đường dẫn ảnh trong code
- **Trước**: `src="/asset/img/banner1.jpg"` (đường dẫn tuyệt đối)
- **Sau**: `src="asset/img/banner1.jpg"` (đường dẫn tương đối)

### 3. Cập nhật các file
- `src/pages/Index.tsx`: Thay đổi đường dẫn ảnh banner và sản phẩm
- `src/pages/Home.tsx`: Thay đổi đường dẫn ảnh logo

## Cấu trúc thư mục sau khi sửa

```
frontend/
├── public/
│   ├── asset/          # ← Đã di chuyển vào đây
│   │   ├── img/
│   │   │   ├── banner1.jpg
│   │   │   ├── banner2.jpg
│   │   │   └── ...
│   │   └── video/
│   ├── _redirects
│   ├── favicon.ico
│   └── ...
├── src/
│   ├── pages/
│   │   ├── Index.tsx   # ← Đã cập nhật đường dẫn
│   │   └── Home.tsx    # ← Đã cập nhật đường dẫn
│   └── ...
└── vite.config.ts      # ← publicDir: 'public'
```

## Kết quả
✅ **Sau khi build**: Thư mục `dist/` chứa đầy đủ các ảnh từ `asset/`
✅ **Khi deploy**: Các ảnh sẽ hiển thị bình thường
✅ **Tương thích**: Hoạt động tốt với các platform deploy (Netlify, Vercel, GitHub Pages)

## Lưu ý
- Với Vite, khi sử dụng `publicDir: 'public'`, các file trong thư mục `public/` sẽ được serve trực tiếp từ root path
- Đường dẫn tương đối (`asset/img/...`) sẽ hoạt động tốt hơn đường dẫn tuyệt đối (`/asset/img/...`) khi deploy
- Luôn đặt các file tĩnh (ảnh, video, CSS, JS) vào thư mục `public/` để Vite có thể copy vào `dist/` khi build

## Test
Để test sau khi build:
```bash
npm run build
serve dist -p 3000
```
Sau đó mở `http://localhost:3000` để kiểm tra các ảnh có hiển thị không.
