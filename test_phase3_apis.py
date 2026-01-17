"""
Phase 3 新模块 API 测试脚本

测试档案管理和对话历史管理的所有接口
"""
import requests
import json
from datetime import date

# API 基地址
BASE_URL = "http://localhost:8000"

# 测试用户 ID
USER_ID = "test_user_123"

def print_response(response):
    """格式化打印响应"""
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应体: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应体: {response.text}")
    print("-" * 80)

def test_profile_apis():
    """测试档案管理 API"""
    print("\n========== 测试档案管理模块 ==========\n")
    
    # 1. 创建档案
    print("1️⃣ 创建孩子档案")
    response = requests.post(
        f"{BASE_URL}/profile",
        headers={"X-User-ID": USER_ID},
        json={
            "nickname": "小明",
            "birth_date": "2017-05-20",
            "grade": "一年级",
            "notes": "性格活泼，喜欢画画"
        }
    )
    print_response(response)
    
    # 2. 查询档案
    print("2️⃣ 查询档案")
    response = requests.get(
        f"{BASE_URL}/profile",
        headers={"X-User-ID": USER_ID}
    )
    print_response(response)
    
    # 3. 更新档案
    print("3️⃣ 更新档案（修改昵称和年级）")
    response = requests.put(
        f"{BASE_URL}/profile",
        headers={"X-User-ID": USER_ID},
        json={
            "nickname": "小明明",
            "grade": "二年级"
        }
    )
    print_response(response)
    
    # 4. 再次查询验证更新
    print("4️⃣ 验证更新结果")
    response = requests.get(
        f"{BASE_URL}/profile",
        headers={"X-User-ID": USER_ID}
    )
    print_response(response)

def test_history_apis():
    """测试对话历史管理 API"""
    print("\n========== 测试对话历史管理模块 ==========\n")
    
    # 1. 创建会话
    print("1️⃣ 创建新会话")
    response = requests.post(
        f"{BASE_URL}/history/session",
        headers={"X-User-ID": USER_ID}
    )
    print_response(response)
    session_id = response.json().get("session_id")
    
    # 2. 添加用户消息
    print("2️⃣ 添加用户消息")
    response = requests.post(
        f"{BASE_URL}/history/message",
        headers={
            "X-User-ID": USER_ID,
            "X-Session-ID": session_id
        },
        json={
            "role": "user",
            "content": "孩子7岁不肯写作业怎么办？"
        }
    )
    print_response(response)
    
    # 3. 添加 AI 回复
    print("3️⃣ 添加 AI 回复")
    response = requests.post(
        f"{BASE_URL}/history/message",
        headers={
            "X-User-ID": USER_ID,
            "X-Session-ID": session_id
        },
        json={
            "role": "assistant",
            "content": "我理解您的焦虑。7岁孩子不愿写作业，通常有以下原因..."
        }
    )
    print_response(response)
    
    # 4. 再添加一轮对话
    print("4️⃣ 添加第二轮对话")
    requests.post(
        f"{BASE_URL}/history/message",
        headers={"X-User-ID": USER_ID, "X-Session-ID": session_id},
        json={"role": "user", "content": "具体应该怎么说？"}
    )
    requests.post(
        f"{BASE_URL}/history/message",
        headers={"X-User-ID": USER_ID, "X-Session-ID": session_id},
        json={"role": "assistant", "content": "第一句可以这样说：'宝贝，你今天..."}
    )
    
    # 5. 查询历史
    print("5️⃣ 查询对话历史")
    response = requests.get(
        f"{BASE_URL}/history",
        headers={
            "X-User-ID": USER_ID,
            "X-Session-ID": session_id
        }
    )
    print_response(response)
    
    # 6. 获取当前会话
    print("6️⃣ 获取当前会话 ID")
    response = requests.get(
        f"{BASE_URL}/history/session",
        headers={"X-User-ID": USER_ID}
    )
    print_response(response)
    
    # 7. 清空会话
    print("7️⃣ 清空会话消息")
    response = requests.delete(
        f"{BASE_URL}/history/session",
        headers={
            "X-User-ID": USER_ID,
            "X-Session-ID": session_id
        }
    )
    print_response(response)
    
    # 8. 验证清空结果
    print("8️⃣ 验证会话已清空")
    response = requests.get(
        f"{BASE_URL}/history",
        headers={
            "X-User-ID": USER_ID,
            "X-Session-ID": session_id
        }
    )
    print_response(response)

def test_integration():
    """集成测试：档案 + 历史"""
    print("\n========== 集成测试：查询档案并创建对话 ==========\n")
    
    # 1. 查询档案获取年龄
    profile_response = requests.get(
        f"{BASE_URL}/profile",
        headers={"X-User-ID": USER_ID}
    )
    
    if profile_response.status_code == 200:
        profile = profile_response.json()
        print(f"✅ 档案信息：{profile['nickname']}，{profile['age']}岁")
        
        # 2. 使用档案信息调用原有的 /chat 接口
        print("\n调用 /chat 接口（使用档案中的年龄）")
        chat_response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": "孩子不爱吃饭怎么办？",
                "response_mode": "concise",
                "child_age": profile["age"],  # 使用档案中的年龄
                "history": []
            }
        )
        print_response(chat_response)

if __name__ == "__main__":
    try:
        # 测试档案管理
        test_profile_apis()
        
        # 测试对话历史管理
        test_history_apis()
        
        # 集成测试
        test_integration()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("❌ 错误：无法连接到服务器")
        print("请确保后端服务已启动：python main.py")
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
