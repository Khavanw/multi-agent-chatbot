
import { Link } from 'react-router-dom';
import './Index.css';

const Index = () => {
  return (
    <div className="index-container">
      {/* Topbar */}
      <div className="topbar">
        <div className="location">
          📍 Bạn muốn giao đến địa chỉ nào? <strong>tây lân, P.Bình Trị Đông, TP.HCM</strong>
        </div>
        <div className="search-bar">
          <input type="text" placeholder="Bạn cần tìm sản phẩm gì?" />
          <button><i className="fas fa-search"></i></button>
        </div>
        <div className="top-icons">
          <i className="fas fa-heart"></i>
          <i className="fas fa-user"></i>
          <i className="fas fa-shopping-cart"></i>
        </div>
      </div>

      {/* Notification */}
      <div className="notification">
        Hệ thống đã hỗ trợ địa chỉ giao hàng theo đơn vị hành chính mới...
      </div>

      {/* Main Nav */}
      <div className="nav">
        <div className="menu">
          <i className="fas fa-th-large"></i> Danh mục sản phẩm
        </div>
        <div className="nav-links">
          <a href="#">Khuyến mãi</a>
          <a href="#">Thương hiệu riêng</a>
          <a href="#">Unilever</a>
          <a href="#">Sản phẩm nhập khẩu</a>
          <a href="#">Ẩn phẩm khuyến mãi</a>
        </div>
      </div>

      {/* Banner area */}
      <div className="banner">
        <img src="/asset/img/banner1.jpg" alt="Dinh dưỡng" />
        <img src="/asset/img/banner2.jpg" alt="4 ngày giá sốc" />
        <img src="/asset/img/banner3.jpg" alt="Celebrating agriculture" />
      </div>

      <section className="promotion-section">
        <div className="promotion-header">
          <div>
            <h2>4 NGÀY GIÁ SỐC</h2>
            <p>Chỉ còn trong: <span id="countdown">03 : 15 : 26</span></p>
          </div>
          <button className="buy-now-btn">Mua Ngay</button>
        </div>

        <div className="products-scroll">
          {/* Sản phẩm */}
          <div className="product-card">
            <img src="/asset/img/sua.jpg" alt="Sữa" />
            <p className="price">63.000 ₫ <span className="old-price">65.000 ₫</span></p>
            <p>Sữa đặc Ngôi Sao</p>
            <button className="detail-btn">Xem chi tiết</button>
          </div>
          <div className="product-card">
            <img src="/asset/img/hat_nem.jpg" alt="Hạt nêm" />
            <p className="price">37.000 ₫ <span className="old-price">37.000 ₫</span></p>
            <p>Hạ nêm vị heo</p>
            <button className="detail-btn">Xem chi tiết</button>
          </div>
          <div className="product-card">
            <img src="/asset/img/bia.jpg" alt="Bia" />
            <p className="price">390.000 ₫ <span className="old-price">37.000 ₫</span></p>
            <p>Bia tiger bạc</p>
            <button className="detail-btn">Xem chi tiết</button>
            </div>
          <div className="product-card">
            <img src="/asset/img/cha_la.jpg" alt="Chà là" />
            <p className="price">49.000 ₫ <span className="old-price">49.000 ₫</span></p>
            <p>Chà là khô Nguyên Cành</p>
            <button className="detail-btn">Xem chi tiết</button>
          </div>
          <div className="product-card">
            <img src="/asset/img/dui_ga.jpg" alt="Dùi gà" />
            <p className="price">39.000 ₫ <span className="old-price">39.000 ₫</span></p>
            <p>Dùi gà tỏi quay, khay 3 cái</p>
            <button className="detail-btn">Xem chi tiết</button>
          </div>
          <div className="product-card">
            <img src="/asset/img/sua_bo.jpg" alt="Sữa bò" />
            <p className="price">35.000 ₫ <span className="old-price">35.000 ₫</span></p>
            <p>Sữa bò tiệt trùng</p>
            <button className="detail-btn">Xem chi tiết</button>
          </div>
        </div>
      </section>

      {/* Floating buttons */}
      <div className="floating-buttons">
        <button title="Lên đầu trang"><i className="fas fa-arrow-up"></i></button>
        <button title="Theo dõi đơn hàng"><i className="fas fa-truck"></i></button>
        <Link to="/home" className="support-btn" title="Hỗ trợ">
          <i className="fas fa-headset"></i>
        </Link>
        <Link to="/food-kit" className="food-kit-btn" title="Kit Thức Ăn">
          <i className="fas fa-utensils"></i>
        </Link>
      </div>
    </div>
  );
};

export default Index;
