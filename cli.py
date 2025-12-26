import argparse
import asyncio
import os

from dotenv import load_dotenv

from src.site_builder import build_site_and_posts
from src.telegram_publisher import publish_posts

def main():
    load_dotenv()

    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Generate static pages into ./site and posts into posts.jsonl")
    p_build.add_argument("--csv", default="topics.csv")
    p_build.add_argument("--site-dir", default="site")
    p_build.add_argument("--posts", default="posts.jsonl")
    p_build.add_argument("--limit", type=int, default=None)

    p_pub = sub.add_parser("publish", help="Publish posts.jsonl to Telegram channel")
    p_pub.add_argument("--posts", default="posts.jsonl")
    p_pub.add_argument("--rate", type=float, default=float(os.getenv("DEFAULT_RATE_PER_MIN", "26")))
    p_pub.add_argument("--limit", type=int, default=None)

    p_all = sub.add_parser("all", help="Build + Publish")
    p_all.add_argument("--csv", default="topics.csv")
    p_all.add_argument("--site-dir", default="site")
    p_all.add_argument("--posts", default="posts.jsonl")
    p_all.add_argument("--rate", type=float, default=float(os.getenv("DEFAULT_RATE_PER_MIN", "26")))
    p_all.add_argument("--limit", type=int, default=None)

    args = ap.parse_args()

    site_base_url = os.getenv("SITE_BASE_URL", "").strip()
    tg_group_url = os.getenv("TG_GROUP_URL", "").strip()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    channel = os.getenv("TELEGRAM_CHANNEL", "").strip()

    if args.cmd in ("build", "all"):
        if not site_base_url:
            raise SystemExit("Set SITE_BASE_URL in .env")
        if not tg_group_url:
            raise SystemExit("Set TG_GROUP_URL in .env (button target)")

        built = build_site_and_posts(
            csv_path=args.csv,
            site_dir=args.site_dir,
            posts_path=args.posts,
            site_base_url=site_base_url,
            tg_group_url=tg_group_url,
            limit=args.limit,
        )
        print(f"Built: {len(built)} items. Site: {args.site_dir}, Posts: {args.posts}")

    if args.cmd in ("publish", "all"):
        if not bot_token:
            raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env")
        if not channel:
            raise SystemExit("Set TELEGRAM_CHANNEL in .env")
        asyncio.run(publish_posts(
            posts_path=args.posts,
            token=bot_token,
            channel=channel,
            rate_per_min=args.rate,
            limit=args.limit,
        ))

if __name__ == "__main__":
    main()
