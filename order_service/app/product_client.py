import os
import httpx
from fastapi import HTTPException, status

DEFAULT_PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")

class ProductClient:
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or DEFAULT_PRODUCT_SERVICE_URL).rstrip("/")

    def get_product(self, product_id: str) -> dict:
        """Fetch product details from Product Service."""
        url = f"{self.base_url}/api/v1/products/{product_id}"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product with ID '{product_id}' not found in catalog"
                    )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Product Service error: {response.text}"
                    )
                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach Product Service at {url}: {str(exc)}"
            )

    def deduct_stock(self, product_id: str, quantity: int) -> dict:
        """Request stock deduction from Product Service."""
        url = f"{self.base_url}/api/v1/products/{product_id}/deduct-stock"
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.patch(url, json={"quantity": quantity})
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product with ID '{product_id}' not found for stock deduction"
                    )
                if response.status_code == 409:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Insufficient stock available"
                    )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Stock deduction error: {response.text}"
                    )
                return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach Product Service at {url}: {str(exc)}"
            )

_default_client = ProductClient()

def get_product_client() -> ProductClient:
    return _default_client
