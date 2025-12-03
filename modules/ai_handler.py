"""
AIモデルの切替とプロンプト管理
"""
import json
from typing import Optional, Dict, Any
import base64
from io import BytesIO

class AIHandler:
    """Claude/ChatGPT切替可能なAIハンドラー"""
    
    def __init__(self, model_type: str, api_key: str):
        """
        Args:
            model_type: 'claude' or 'openai'
            api_key: APIキー
        """
        self.model_type = model_type.lower()
        self.api_key = api_key
        
        if self.model_type == 'claude':
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model_name = "claude-sonnet-4-20250514"
        elif self.model_type == 'openai':
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            self.model_name = "gpt-4o-mini"
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def analyze_text(self, system_prompt: str, user_prompt: str, 
                     max_tokens: int = 2000) -> Dict[str, Any]:
        """
        テキスト分析を実行
        
        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            max_tokens: 最大トークン数
            
        Returns:
            分析結果のJSON
        """
        try:
            if self.model_type == 'claude':
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                result_text = response.content[0].text
            else:  # openai
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens
                )
                result_text = response.choices[0].message.content
            
            # JSONをパース（マークダウンブロックを除去）
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            return json.loads(result_text)
        except json.JSONDecodeError as e:
            # JSON解析失敗時はエラーレスポンスを返す
            return {
                "error": "JSON解析エラー",
                "details": str(e),
                "raw_response": result_text[:500]
            }
        except Exception as e:
            return {
                "error": "API呼び出しエラー",
                "details": str(e)
            }
    
    def analyze_image(self, system_prompt: str, user_prompt: str, 
                     image_data: bytes, max_tokens: int = 2000) -> Dict[str, Any]:
        """
        画像分析を実行
        
        Args:
            system_prompt: システムプロンプト
            user_prompt: ユーザープロンプト
            image_data: 画像データ（バイト列）
            max_tokens: 最大トークン数
            
        Returns:
            分析結果のJSON
        """
        try:
            # 画像をBase64エンコード
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            if self.model_type == 'claude':
                # Claude APIの画像処理
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_base64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": user_prompt
                                }
                            ]
                        }
                    ]
                )
                result_text = response.content[0].text
            else:  # openai
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": user_prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=max_tokens
                )
                result_text = response.choices[0].message.content
            
            # JSONをパース
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            return json.loads(result_text)
        except json.JSONDecodeError as e:
            return {
                "error": "JSON解析エラー",
                "details": str(e),
                "raw_response": result_text[:500]
            }
        except Exception as e:
            return {
                "error": "API呼び出しエラー",
                "details": str(e)
            }
