import os
from huggingface_hub import HfApi

def main():
    local_file = "connect-ai/connect-ai-brain.jsonl"
    if not os.path.exists(local_file):
        print(f"Error: {local_file} not found. Please make sure you are in the project root directory.")
        return

    # Try to load cached Hugging Face token
    token_path = os.path.expanduser("~/.cache/huggingface/token")
    token = None
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()

    if not token:
        token = input("HuggingFace Write Token을 입력하세요: ").strip()

    if not token:
        print("토큰이 입력되지 않아 업로드를 취소합니다.")
        return

    api = HfApi(token=token)
    try:
        user_info = api.whoami()
        username = user_info["name"]
        repo_id = f"{username}/connect-ai-brain"
        
        print(f"\nHF 계정: {username}")
        print(f"업로드 대상 레포지토리: {repo_id}")
        print("업로드를 시작합니다...")
        
        api.upload_file(
            path_or_fileobj=local_file,
            path_in_repo="connect-ai-brain.jsonl",
            repo_id=repo_id,
            repo_type="dataset",
            token=token
        )
        print("\n✅ 업로드 완료! Hugging Face 데이터셋에 정상 반영되었습니다.")
        print(f"확인 링크: https://huggingface.co/datasets/{repo_id}")
    except Exception as e:
        print(f"\n❌ 업로드 실패: {e}")

if __name__ == "__main__":
    main()
