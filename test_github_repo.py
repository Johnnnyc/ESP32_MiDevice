import requests
import json
from config import GITHUB_REPO

def check_github_repo():
    """检查GitHub仓库是否存在"""
    repo_url = f"https://api.github.com/repos/{GITHUB_REPO}"
    print(f"检查GitHub仓库: {GITHUB_REPO}")
    print(f"API URL: {repo_url}")
    
    try:
        response = requests.get(repo_url)
        if response.status_code == 200:
            data = response.json()
            print("仓库存在!")
            print(f"仓库名称: {data.get('name')}")
            print(f"描述: {data.get('description')}")
            print(f"星标数: {data.get('stargazers_count')}")
            print(f"分支数: {data.get('forks_count')}")
            return True
        else:
            print(f"仓库不存在或无法访问: {response.status_code}")
            return False
    except Exception as e:
        print(f"检查仓库时出错: {e}")
        return False

def check_releases():
    """检查GitHub仓库的发布版本"""
    releases_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    print(f"\n检查发布版本: {releases_url}")
    
    try:
        response = requests.get(releases_url)
        if response.status_code == 200:
            releases = response.json()
            if releases:
                print(f"找到 {len(releases)} 个发布版本:")
                for release in releases:
                    tag_name = release.get('tag_name')
                    name = release.get('name')
                    published_at = release.get('published_at')
                    print(f"- {tag_name}: {name} (发布于: {published_at})")
            else:
                print("仓库没有发布版本")
        else:
            print(f"获取发布版本失败: {response.status_code}")
    except Exception as e:
        print(f"检查发布版本时出错: {e}")

def main():
    print("GitHub仓库检查测试程序")
    print("=" * 50)
    
    # 检查仓库是否存在
    repo_exists = check_github_repo()
    
    if repo_exists:
        # 检查发布版本
        check_releases()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()
