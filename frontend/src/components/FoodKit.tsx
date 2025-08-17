import React, { useState } from 'react';
import './FoodKit.css';

interface FoodItem {
  id: number;
  name: string;
  image: string;
  price: number;
  originalPrice?: number;
  category: string;
  description: string;
  rating: number;
  isNew?: boolean;
  isHot?: boolean;
}

const FoodKit: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('popular');

  const foodItems: FoodItem[] = [
    {
      id: 1,
      name: "Sữa đặc Ngôi Sao",
      image: "/asset/img/sua.jpg",
      price: 63000,
      originalPrice: 65000,
      category: "dairy",
      description: "Sữa đặc có đường, giàu dinh dưỡng cho gia đình",
      rating: 4.5,
      isHot: true
    },
    {
      id: 2,
      name: "Hạt nêm vị heo",
      image: "/asset/img/hat_nem.jpg",
      price: 37000,
      category: "seasoning",
      description: "Hạt nêm tự nhiên, tăng hương vị món ăn",
      rating: 4.3
    },
    {
      id: 3,
      name: "Bia Tiger Bạc",
      image: "/asset/img/bia.jpg",
      price: 390000,
      originalPrice: 420000,
      category: "beverage",
      description: "Bia lager mát lạnh, hương vị đậm đà",
      rating: 4.7,
      isNew: true
    },
    {
      id: 4,
      name: "Chà là khô Nguyên Cành",
      image: "/asset/img/cha_la.jpg",
      price: 49000,
      category: "snack",
      description: "Chà là khô tự nhiên, giàu dinh dưỡng",
      rating: 4.6
    },
    {
      id: 5,
      name: "Dùi gà tỏi quay",
      image: "/asset/img/dui_ga.jpg",
      price: 39000,
      category: "meat",
      description: "Dùi gà tẩm tỏi, hương vị thơm ngon",
      rating: 4.4,
      isHot: true
    },
    {
      id: 6,
      name: "Sữa bò tiệt trùng",
      image: "/asset/img/sua_bo.jpg",
      price: 35000,
      originalPrice: 38000,
      category: "dairy",
      description: "Sữa bò tươi tiệt trùng, giàu canxi",
      rating: 4.8
    }
  ];

  const categories = [
    { id: 'all', name: 'Tất cả', icon: '🍽️' },
    { id: 'dairy', name: 'Sữa & Bơ', icon: '🥛' },
    { id: 'meat', name: 'Thịt & Cá', icon: '🥩' },
    { id: 'seasoning', name: 'Gia vị', icon: '🧂' },
    { id: 'beverage', name: 'Đồ uống', icon: '🥤' },
    { id: 'snack', name: 'Đồ ăn vặt', icon: '🍿' }
  ];

  const filteredItems = foodItems.filter(item => 
    selectedCategory === 'all' || item.category === selectedCategory
  );

  const sortedItems = [...filteredItems].sort((a, b) => {
    switch (sortBy) {
      case 'price-low':
        return a.price - b.price;
      case 'price-high':
        return b.price - a.price;
      case 'rating':
        return b.rating - a.rating;
      default:
        return b.rating - a.rating; // popular
    }
  });

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  };

  return (
    <div className="food-kit-container">
      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="gradient-text">Kit Thức Ăn</span>
            <br />
            <span className="subtitle">Dinh Dưỡng & Hương Vị</span>
          </h1>
          <p className="hero-description">
            Khám phá bộ sưu tập thực phẩm chất lượng cao, đa dạng hương vị 
            cho bữa ăn gia đình hoàn hảo
          </p>
          <div className="hero-stats">
            <div className="stat-item">
              <span className="stat-number">50+</span>
              <span className="stat-label">Sản phẩm</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">4.8★</span>
              <span className="stat-label">Đánh giá</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">24h</span>
              <span className="stat-label">Giao hàng</span>
            </div>
          </div>
        </div>
        <div className="hero-image">
          <img src="/asset/img/banner1.jpg" alt="Kit thức ăn" />
        </div>
      </div>

      {/* Category Filter */}
      <div className="category-section">
        <div className="category-tabs">
          {categories.map(category => (
            <button
              key={category.id}
              className={`category-tab ${selectedCategory === category.id ? 'active' : ''}`}
              onClick={() => setSelectedCategory(category.id)}
            >
              <span className="category-icon">{category.icon}</span>
              <span className="category-name">{category.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Sort Options */}
      <div className="sort-section">
        <div className="sort-options">
          <label>Sắp xếp theo:</label>
          <select 
            value={sortBy} 
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="popular">Phổ biến</option>
            <option value="rating">Đánh giá cao</option>
            <option value="price-low">Giá tăng dần</option>
            <option value="price-high">Giá giảm dần</option>
          </select>
        </div>
      </div>

      {/* Products Grid */}
      <div className="products-grid">
        {sortedItems.map(item => (
          <div key={item.id} className="product-card">
            <div className="product-badges">
              {item.isNew && <span className="badge new">Mới</span>}
              {item.isHot && <span className="badge hot">Hot</span>}
              {item.originalPrice && (
                <span className="badge discount">
                  -{Math.round(((item.originalPrice - item.price) / item.originalPrice) * 100)}%
                </span>
              )}
            </div>
            
            <div className="product-image">
              <img src={item.image} alt={item.name} />
              <div className="product-overlay">
                <button className="quick-view-btn">
                  <i className="fas fa-eye"></i>
                </button>
                <button className="add-to-cart-btn">
                  <i className="fas fa-shopping-cart"></i>
                </button>
              </div>
            </div>

            <div className="product-info">
              <div className="product-category">{item.category}</div>
              <h3 className="product-name">{item.name}</h3>
              <p className="product-description">{item.description}</p>
              
              <div className="product-rating">
                <div className="stars">
                  {[...Array(5)].map((_, i) => (
                    <i 
                      key={i} 
                      className={`fas fa-star ${i < Math.floor(item.rating) ? 'filled' : ''}`}
                    ></i>
                  ))}
                </div>
                <span className="rating-text">{item.rating}</span>
              </div>

              <div className="product-price">
                <span className="current-price">{formatPrice(item.price)}</span>
                {item.originalPrice && (
                  <span className="original-price">{formatPrice(item.originalPrice)}</span>
                )}
              </div>

              <div className="product-actions">
                <button className="add-to-cart">
                  <i className="fas fa-shopping-cart"></i>
                  Thêm vào giỏ
                </button>
                <button className="wishlist">
                  <i className="fas fa-heart"></i>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Special Offers */}
      <div className="special-offers">
        <h2 className="section-title">Ưu Đãi Đặc Biệt</h2>
        <div className="offers-grid">
          <div className="offer-card">
            <img src="/asset/img/banner2.jpg" alt="Khuyến mãi" />
            <div className="offer-content">
              <h3>4 Ngày Giá Sốc</h3>
              <p>Giảm giá lên đến 50% cho các sản phẩm bán chạy</p>
              <button className="offer-btn">Xem ngay</button>
            </div>
          </div>
          <div className="offer-card">
            <img src="/asset/img/banner3.jpg" alt="Nông nghiệp" />
            <div className="offer-content">
              <h3>Sản Phẩm Nông Nghiệp</h3>
              <p>Thực phẩm sạch, an toàn từ nông trại đến bàn ăn</p>
              <button className="offer-btn">Khám phá</button>
            </div>
          </div>
        </div>
      </div>

      {/* Newsletter */}
      <div className="newsletter-section">
        <div className="newsletter-content">
          <h2>Đăng Ký Nhận Tin</h2>
          <p>Nhận thông báo về ưu đãi mới nhất và sản phẩm hot</p>
          <div className="newsletter-form">
            <input 
              type="email" 
              placeholder="Nhập email của bạn..." 
              className="newsletter-input"
            />
            <button className="newsletter-btn">
              <i className="fas fa-paper-plane"></i>
              Đăng ký
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FoodKit;
