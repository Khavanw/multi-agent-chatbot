# Message Grouping Fix - Giải pháp cho vấn đề phản hồi bị tách thành nhiều block

## Vấn đề ban đầu

Khi người dùng gửi nhiều tin nhắn liên tiếp, phần phản hồi từ Mega Agent hiển thị bị tách thành nhiều block khác nhau thay vì gộp vào cùng một nhóm phản hồi cho cùng một lượt tương tác.

### Nguyên nhân:
1. **Backend streaming response**: Backend gửi nhiều chunk data riêng biệt
2. **Thiếu logic grouping**: UI không có cơ chế để nhóm các message liên tiếp từ cùng một session
3. **Không có session tracking**: Không có cách để nhận diện các response thuộc cùng một request

## Giải pháp đã implement

### 1. Thêm Session Tracking
```typescript
interface Message {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: Date;
  sessionId?: string; // Thêm sessionId để nhóm các message liên tiếp
  isStreaming?: boolean; // Đánh dấu message đang streaming
}
```

### 2. Cải thiện Streaming Response Handling
- **Throttling**: Chỉ update UI mỗi 100ms để tránh spam
- **Content merging**: Logic để merge content từ các response fragment
- **Session-based grouping**: Nhóm các message theo sessionId

### 3. Message Grouping Logic
```typescript
const groupMessagesBySession = (messages: Message[]) => {
  // Logic để nhóm các message liên tiếp từ cùng một session
  // Bot messages cùng session sẽ được hiển thị trong cùng một block
}
```

### 4. Visual Improvements
- **Message groups**: CSS styling cho grouped messages
- **Streaming indicators**: Visual feedback cho messages đang streaming
- **Smooth transitions**: Animation cho message groups

### 5. Responsive Image Styling
- **Product grid**: Responsive grid layout cho product cards
- **Image containers**: Aspect ratio 16:9 với object-fit cover
- **Hover effects**: Smooth transitions và scale effects
- **Mobile optimization**: Adaptive sizing cho các screen sizes khác nhau

### 6. Sidebar Chat History Styling
- **Modern design**: Clean và professional appearance
- **Active state indicators**: Visual feedback cho conversation hiện tại
- **Hover effects**: Smooth transitions và animations
- **Delete button**: Animated delete functionality
- **Responsive design**: Adaptive sizing cho mobile devices

### 7. Message Content Display Fix
- **Content visibility**: Đảm bảo tin nhắn luôn hiển thị đúng
- **Empty content handling**: Placeholder cho content trống
- **Text formatting**: Proper styling cho links, lists, và formatting
- **Loading states**: Visual feedback cho messages đang loading
- **Debug information**: Development mode debugging

### 8. Mobile Performance Optimizations
- **Touch optimizations**: Better touch targets và feedback
- **Scroll performance**: Optimized scrolling cho mobile devices
- **Image loading**: Mobile-optimized image loading và error handling
- **Memory management**: Efficient memory usage và cleanup
- **Responsive design**: Adaptive sizing cho mọi screen sizes
- **Performance optimizations**: Reduced motion, high DPI support

### 9. Research Agent Response Handling
- **Format detection**: Automatic detection của Research Agent response format
- **Structured parsing**: Parse agent và tools sections riêng biệt
- **Visual separation**: Distinct styling cho agent và tools content
- **Fallback handling**: Graceful fallback cho unstructured content
- **Multiple patterns**: Support cho nhiều format patterns khác nhau

### 10. Agent Name Detection Fix
- **Content-based detection**: Detect agent type dựa trên content thực tế
- **Dynamic naming**: Hiển thị tên agent chính xác dựa trên response format
- **Visual distinction**: Styling khác biệt cho từng loại agent
- **Fallback logic**: Graceful fallback cho các trường hợp không xác định được
- **Agent type storage**: Lưu trữ agentType trong message để đảm bảo tên chính xác
- **Session-based naming**: Sử dụng agent được chọn khi gửi message

### 11. Agent Selection UI
- **Multi-agent support**: 4 agent buttons với distinct functionality
- **Default supervisor**: VITE_AGENT_SUPERVISOR làm agent mặc định
- **Dynamic API routing**: Tự động chọn API endpoint dựa trên agent được chọn
- **Visual feedback**: Color-coded buttons với hover effects
- **Responsive design**: Adaptive sizing cho mobile devices

### 12. Voice Input Feature
- **Voice recording**: Ghi âm giọng nói sử dụng MediaRecorder API
- **WAV conversion**: Chuyển đổi audio thành WAV format với proper headers
- **FormData transmission**: Gửi file WAV dưới dạng FormData với binary file
- **STT integration**: Gửi audio đến backend để chuyển đổi thành text
- **Auto-send**: Tự động gửi text đã chuyển đổi đến Agent Supervisor
- **Visual feedback**: Button animation và recording indicators
- **Error handling**: Graceful error handling cho microphone access và API calls

## Các thay đổi chính

### Home.tsx
1. **Thêm sessionId tracking** trong Message interface
2. **Cải thiện handleStreamingResponse** với throttling và content merging
3. **Thêm groupMessagesBySession** function
4. **Cập nhật render logic** để sử dụng message groups
5. **Cải thiện scroll behavior** cho streaming messages
6. **Agent selection system**:
   - Thay thế isVectorDbMode bằng selectedAgent state
   - Thêm getApiUrl() function để dynamic API routing
   - Thêm getAgentDisplayName() function cho consistent naming
   - Cập nhật detectAgentType() để sử dụng selected agent
   - Thêm agentType vào Message interface để lưu trữ loại agent
   - Cập nhật getMessageAgentName() để ưu tiên agentType từ message
7. **Multi-agent UI**:
   - 4 agent buttons với distinct styling
   - Color-coded buttons (Supervisor: gold, Mega: blue, Research: green, Agent1: red)
   - Responsive design cho mobile
   - Hover effects và active states
8. **Voice input functionality**:
   - MediaRecorder API integration cho voice recording
   - Audio to WAV conversion với proper headers
   - WAV to FormData transmission
   - STT API integration với VITE_VOICE_STT_URL
   - Auto-send transcribed text đến Agent Supervisor
   - Recording state management và visual feedback

### Home.css
1. **Message group styling** với visual separation
2. **Streaming indicators** với animation
3. **Grouped message styling** với hover effects
4. **Smooth transitions** cho message groups
5. **Product grid responsive design**:
   - Desktop: 3-4 columns với minmax(280px, 1fr)
   - Tablet: 2-3 columns với minmax(240px, 1fr)
   - Mobile: 2 columns với adaptive sizing
6. **Image responsive styling**:
   - Aspect ratio 16:9 cho consistent sizing
   - Object-fit cover để maintain proportions
   - Hover effects với scale và shadow
   - Loading states với fallback icons
7. **Sidebar chat history styling**:
   - Modern design với gradient backgrounds
   - Active state indicators với blue accent
   - Hover effects với smooth transitions
   - Animated delete buttons
   - Responsive design cho mobile
   - Custom scrollbar styling
8. **Mobile performance optimizations**:
   - Touch-optimized interactions
   - Mobile-specific scroll behavior
   - Optimized image loading
   - Reduced motion support
   - High DPI display support
   - Performance-focused CSS
9. **Research Agent response styling**:
   - Distinct visual separation cho agent và tools sections
   - Icon indicators (🤖 cho agent, 🔍 cho tools)
   - Gradient backgrounds với color coding
   - Responsive design cho mobile
   - Proper text formatting và styling
10. **Agent name detection và styling**:
    - Content-based agent type detection
    - Dynamic agent name display
    - Visual distinction với colored dots
    - Responsive design cho mobile
    - Fallback logic cho edge cases
11. **Agent selection buttons styling**:
    - Modern button design với gradient backgrounds
    - Color-coded buttons cho từng agent type
    - Hover effects với shine animation
    - Active state indicators
    - Responsive design cho mobile
    - Touch optimizations cho mobile devices
12. **Voice button styling**:
    - Circular button design với gradient backgrounds
    - Recording state với pulse animation
    - Hover effects với shine animation
    - Disabled state styling
    - Responsive design cho mobile
    - Touch optimizations cho mobile devices

## Kết quả

### Trước khi fix:
- Mỗi response fragment tạo ra một message riêng biệt
- Phản hồi bị tách thành nhiều block không liên quan
- UX kém, khó theo dõi conversation flow
- Images không responsive, bị méo hoặc không cân đối

### Sau khi fix:
- Các response fragment được merge vào cùng một message
- Messages cùng session được nhóm lại với nhau
- Visual separation rõ ràng giữa các conversation
- Smooth streaming với visual feedback
- Performance tốt hơn với throttling
- **Images responsive và cân đối**:
  - Tỷ lệ khung hình nhất quán (16:9)
  - Adaptive sizing cho mọi thiết bị
  - Smooth hover effects
  - Loading states với fallback

## Responsive Design Features

### Product Grid
- **Desktop (1200px+)**: 3-4 columns, minmax(280px, 1fr)
- **Tablet (768px-1200px)**: 2-3 columns, minmax(240px, 1fr)
- **Mobile (480px-768px)**: 2 columns, adaptive sizing
- **Small Mobile (<480px)**: 2 columns, compact layout

### Image Containers
- **Aspect ratio**: 16:9 cho consistency
- **Object-fit**: cover để maintain proportions
- **Min-height**: Adaptive (160px → 140px → 100px → 80px)
- **Border radius**: Responsive (12px → 10px → 8px)

### Hover Effects
- **Scale**: 1.08x cho product images, 1.1x cho message images
- **Shadow**: Enhanced shadow on hover
- **Transition**: Smooth 0.3-0.4s cubic-bezier transitions

## Testing

Để test fix này:
1. Gửi một câu hỏi về sản phẩm
2. Quan sát response streaming
3. Kiểm tra xem các sản phẩm có được hiển thị trong cùng một block không
4. Gửi tin nhắn tiếp theo và kiểm tra separation
5. **Test responsive design**:
   - Resize browser window
   - Test trên mobile devices
   - Kiểm tra image proportions
   - Verify hover effects

## Performance Considerations

- **Throttling**: UI updates được throttle để tránh spam
- **Debounced scrolling**: Scroll behavior được optimize
- **Efficient grouping**: Message grouping chỉ tính toán khi cần thiết
- **Memory management**: Proper cleanup của streaming states
- **Image optimization**: Lazy loading và proper aspect ratios
- **CSS optimization**: Efficient selectors và minimal reflows
