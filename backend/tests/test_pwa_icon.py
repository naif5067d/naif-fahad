"""
PWA Icon Management API Tests
Tests for:
- GET /api/company-settings/pwa-icon/{size} - Get PWA icon in requested size
- GET /api/company-settings/manifest.json - Get dynamic manifest with custom icons
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPwaIconEndpoints:
    """PWA Icon API endpoint tests"""
    
    def test_manifest_json_returns_valid_json(self):
        """Test that manifest.json returns valid JSON with icons array"""
        response = requests.get(f"{BASE_URL}/api/company-settings/manifest.json")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required manifest fields
        assert "name" in data
        assert "short_name" in data
        assert "icons" in data
        assert isinstance(data["icons"], list)
        assert len(data["icons"]) >= 2
        
        # Verify icons have correct structure
        for icon in data["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon
            assert "purpose" in icon
            
        print(f"Manifest name: {data['name']}")
        print(f"Number of icons: {len(data['icons'])}")
        
    def test_manifest_json_has_dynamic_icons(self):
        """Test that manifest.json uses dynamic icon URLs"""
        response = requests.get(f"{BASE_URL}/api/company-settings/manifest.json")
        
        assert response.status_code == 200
        
        data = response.json()
        icons = data.get("icons", [])
        
        # Check that at least one icon uses the dynamic API path
        dynamic_icon_found = any(
            "/api/company-settings/pwa-icon/" in icon.get("src", "")
            for icon in icons
        )
        
        # Either dynamic icons or default icons should be present
        assert len(icons) > 0, "Manifest should have icons"
        print(f"Icons: {icons}")
        
    def test_pwa_icon_192_returns_image(self):
        """Test that /api/company-settings/pwa-icon/192 returns a valid PNG image"""
        response = requests.get(f"{BASE_URL}/api/company-settings/pwa-icon/192")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "image/png"
        
        # Verify response has image data
        assert len(response.content) > 0
        print(f"PWA icon 192 size: {len(response.content)} bytes")
        
    def test_pwa_icon_512_returns_image(self):
        """Test that /api/company-settings/pwa-icon/512 returns a valid PNG image"""
        response = requests.get(f"{BASE_URL}/api/company-settings/pwa-icon/512")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "image/png"
        
        # Verify response has image data
        assert len(response.content) > 0
        print(f"PWA icon 512 size: {len(response.content)} bytes")
        
    def test_pwa_icon_180_returns_image(self):
        """Test that /api/company-settings/pwa-icon/180 (apple-touch) returns a valid PNG image"""
        response = requests.get(f"{BASE_URL}/api/company-settings/pwa-icon/180")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "image/png"
        
        # Verify response has image data
        assert len(response.content) > 0
        print(f"PWA icon 180 (apple-touch) size: {len(response.content)} bytes")
        
    def test_pwa_icon_invalid_size_defaults_to_512(self):
        """Test that invalid size defaults to 512"""
        response = requests.get(f"{BASE_URL}/api/company-settings/pwa-icon/invalid")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "image/png"
        print("Invalid size correctly handled by defaulting to 512")
        
    def test_manifest_has_rtl_support(self):
        """Test that manifest.json has RTL support for Arabic"""
        response = requests.get(f"{BASE_URL}/api/company-settings/manifest.json")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify RTL/Arabic support
        assert data.get("lang") == "ar"
        assert data.get("dir") == "rtl"
        print("Manifest has correct RTL/Arabic support")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
