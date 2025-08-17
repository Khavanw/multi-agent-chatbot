# Hướng dẫn Deployment

## Vấn đề đã được giải quyết

Trước đây, dự án có 2 phần riêng biệt:
1. **React App** (trong `src/`) - được build bởi Vite
2. **HTML tĩnh** (`home.html`, `index.html`) - không được xử lý bởi Vite

Điều này gây ra vấn đề khi deploy vì:
- Vite chỉ build phần React app
- Các file HTML tĩnh không được xử lý
- Điều hướng giữa các trang không hoạt động

## Giải pháp đã áp dụng

### 1. Chuyển đổi sang React Router
- Tạo component `Home.tsx` trong `src/pages/` 
- Chuyển toàn bộ logic từ `home.js` sang React component
- Sử dụng React Router để điều hướng

### 2. Cập nhật routing
- Thêm route `/home` trong `App.tsx`
- Cập nhật link trong `index.html` từ `home.html` thành `/home`

### 3. Cấu hình deployment
- Thêm file `_redirects` cho Netlify
- Thêm file `vercel.json` cho Vercel
- Cập nhật `vite.config.ts` với cấu hình build

## Cách deploy

### Vercel
```bash
npm run build
# Deploy thư mục dist lên Vercel
```

### Netlify
```bash
npm run build
# Deploy thư mục dist lên Netlify
```

### GitHub Pages
```bash
npm run build
# Deploy thư mục dist lên GitHub Pages
```

## Cấu trúc mới

```
src/
├── pages/
│   ├── Index.tsx      # Trang chủ (MM Mega Market)
│   ├── Home.tsx       # Trang chat (thay thế home.html)
│   └── NotFound.tsx   # Trang 404
├── components/
│   └── ChatInterface.tsx
└── App.tsx           # Router configuration
```

## Lưu ý

- Tất cả assets (hình ảnh, CSS) đã được chuyển vào React app
- LocalStorage vẫn hoạt động bình thường
- Tất cả chức năng chat được giữ nguyên
- Responsive design được duy trì

## Kiểm tra

1. Chạy `npm run dev` để test locally
2. Truy cập `http://localhost:8080` (trang chủ)
3. Click nút "Hỗ trợ" để chuyển đến `/home` (trang chat)
4. Test tất cả chức năng chat 