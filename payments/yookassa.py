import aiohttp
import json
from typing import Optional, Dict
import base64

class YooKassaClient:
    def __init__(self, shop_id: str, secret_key: str):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.auth = aiohttp.BasicAuth(shop_id, secret_key)
        self.base_url = "https://api.yookassa.ru/v3"
    
    async def create_payment(
        self,
        amount: int,
        description: str,
        user_id: int,
        return_url: str,
        metadata: Dict = None
    ) -> Dict:
        """Создает платеж и возвращает ссылку для оплаты"""
        url = f"{self.base_url}/payments"
        
        payload = {
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "payment_method_data": {
                "type": "bank_card"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                **(metadata or {})
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, auth=self.auth, json=payload) as response:
                return await response.json()
    
    async def get_payment(self, payment_id: str) -> Dict:
        """Получает информацию о платеже"""
        url = f"{self.base_url}/payments/{payment_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=self.auth) as response:
                return await response.json()
    
    async def capture_payment(self, payment_id: str) -> Dict:
        """Подтверждает платеж (для двухстадийных)"""
        url = f"{self.base_url}/payments/{payment_id}/capture"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, auth=self.auth, json={}) as response:
                return await response.json()