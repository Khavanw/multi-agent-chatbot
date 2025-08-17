import React from 'react';
import FoodKit from '../components/FoodKit';
import { Link } from 'react-router-dom';
import './FoodKitDemo.css';

const FoodKitDemo: React.FC = () => {
  return (
    <div className="food-kit-demo">
      {/* Navigation Header */}
      <header className="demo-header">
        <div className="header-content">
          <Link to="/" className="back-btn">
            <i className="fas fa-arrow-left"></i>
            Quay lại
          </Link>
          <h1 className="demo-title">Kit Thức Ăn - Demo</h1>
          <div className="header-actions">
            <button className="theme-toggle">
              <i className="fas fa-moon"></i>
            </button>
          </div>
        </div>
      </header>

      {/* FoodKit Component */}
      <FoodKit />

      {/* Footer */}
      <footer className="demo-footer">
        <div className="footer-content">
          <p>&copy; 2024 Technominds AI - Kit Thức Ăn Demo</p>
          <div className="footer-links">
            <a href="#">Về chúng tôi</a>
            <a href="#">Liên hệ</a>
            <a href="#">Chính sách</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default FoodKitDemo;
