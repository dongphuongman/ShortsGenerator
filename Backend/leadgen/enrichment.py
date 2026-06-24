import json
import re
from typing import Optional
from termcolor import colored
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gpt import generate_response


AI_MODEL = "g4f"


def enrich_campaign_description(description: str) -> dict:
    prompt = f"""
You are an expert lead generation strategist. A user describes their business offering.
Analyze it and return a JSON object with:

1. "refined_name": A short, catchy campaign name (max 5 words)
2. "keywords": An array of 10-15 high-intent search keywords/phrases people actively looking for this solution would use
3. "competitor_keywords": An array of 5-8 competitor or alternative names/tools people compare against
4. "target_audience": A 2-3 sentence description of the ideal target audience
5. "intent_queries": An array of 8-12 example posts/questions a potential buyer might write on social media
6. "pain_points": An array of 5-7 pain points or problems this offering solves
7. "steal_audience_angle": A 2-3 sentence strategy on how to identify and engage people who follow/engage with competitors

Return ONLY valid JSON. No markdown, no explanation.

User describes their offering:
{description}
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                print(colored(f"[-] Failed to parse enrichment JSON from GPT", "red"))
                print(colored(f"    Raw: {raw[:300]}", "yellow"))
                result = _fallback_enrichment(description)
        else:
            result = _fallback_enrichment(description)

    required_keys = ["refined_name", "keywords", "competitor_keywords", "target_audience", "intent_queries", "pain_points", "steal_audience_angle"]
    for key in required_keys:
        if key not in result:
            result[key] = _default_for_key(key, description)

    return result


def enhance_profile_analysis(profile: dict) -> dict:
    prompt = f"""
You are a social media audience intelligence analyst. Given a Twitter/X profile, analyze it and return a JSON object with:

1. "audience_demographics": 2-3 sentence estimate of their follower demographics
2. "content_themes": Array of 5-7 content themes/topics this account posts about
3. "engagement_hooks": Array of 4-6 patterns this account uses that drive engagement
4. "steal_audience_strategy": 3-4 sentence strategy on how to replicate or redirect this audience
5. "competitor_overlap": Array of 3-5 types of accounts or brands that share this audience
6. "recommended_outreach": 2-3 sentence approach for engaging this account's followers
7. "intent_signals": Array of 3-5 signals to look for in this account's posts that indicate buying intent

Profile data:
{json.dumps(profile, indent=2)}

Return ONLY valid JSON. No markdown, no explanation.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                print(colored(f"[-] Failed to parse profile analysis JSON from GPT", "red"))
                result = {
                    "audience_demographics": "Analysis unavailable",
                    "content_themes": [],
                    "engagement_hooks": [],
                    "steal_audience_strategy": "Analysis unavailable",
                    "competitor_overlap": [],
                    "recommended_outreach": "Analysis unavailable",
                    "intent_signals": []
                }
        else:
            result = {
                "audience_demographics": "Analysis unavailable",
                "content_themes": [],
                "engagement_hooks": [],
                "steal_audience_strategy": "Analysis unavailable",
                "competitor_overlap": [],
                "recommended_outreach": "Analysis unavailable",
                "intent_signals": []
            }

    return result


def find_related_niche_queries(profile: dict) -> list[str]:
    prompt = f"""
You are a social media audience researcher. Given a Twitter/X profile, generate 5 search queries to find OTHER accounts in the same niche.

These queries should surface accounts with overlapping audiences, similar content focus, or competitor accounts.

Return ONLY a JSON array of 5 search query strings. No markdown.

Profile:
- Username: @{profile.get("username", "")}
- Display name: {profile.get("display_name", "")}
- Bio: {profile.get("bio", "")}
- Follower count: {profile.get("follower_count", "N/A")}
- Following count: {profile.get("following_count", "N/A")}
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result[:10]
    except json.JSONDecodeError:
        pass
    return [f"{profile.get('username', '')} niche"]


def suggest_engagement(post_texts: list[str], campaign_description: str) -> list[str]:
    prompt = f"""
You are a social media engagement strategist. Given a list of social media posts found for a campaign, suggest specific, actionable replies that the user can post to engage with each author.

For each post, write a short reply (1-2 sentences) that:
- Adds value to the conversation
- Subtly positions the user's offering as a solution
- Doesn't sound salesy or spammy
- Matches the tone of the original post

Campaign description: {campaign_description}

Posts:
{json.dumps(post_texts, indent=2)}

Return a JSON array of reply suggestions, one per post. Each entry should have:
- "post_index": index of the post
- "reply": the suggested reply text
- "angle": brief note on why this angle works

Return ONLY valid JSON. No markdown.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    return []


def generate_search_queries(description: str, platform: str) -> list[str]:
    prompt = f"""
Generate 10 advanced search queries for {platform} to find people actively looking for a solution like this:

Offering description: {description}

Return a JSON array of strings. Each query should be a realistic {platform} search that surfaces buying intent.
Return ONLY the JSON array. No markdown.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    return [description]


def enrich_campaign_with_website(description: str, website_data: dict) -> dict:
    site_summary = website_data.get("summary", "")[:2000]
    site_title = website_data.get("title", "")
    site_headings = "\n".join(website_data.get("headings", []))[:1000]

    prompt = f"""
You are an expert lead generation strategist. A user describes their business offering and provides scraped content from their website.

Analyze both and return a JSON object with:

1. "refined_name": A short, catchy campaign name (max 5 words)
2. "keywords": An array of 10-15 high-intent search keywords/phrases people actively looking for this solution would use
3. "competitor_keywords": An array of 5-8 competitor or alternative names/tools people compare against
4. "target_audience": A 2-3 sentence description of the ideal target audience, enriched with details from the website
5. "intent_queries": An array of 8-12 example posts/questions a potential buyer might write on social media
6. "pain_points": An array of 5-7 pain points or problems this offering solves, derived from both the description and website content
7. "steal_audience_angle": A 2-3 sentence strategy on how to identify and engage people who follow/engage with competitors
8. "competitor_tracking": An array of 3-5 likely competitor names or brands that operate in this space (extract from website context if possible)
9. "viral_content_angles": An array of 3-4 content angles that could generate high engagement for this niche
10. "value_proposition": A single sentence summarizing the core value proposition from the website

Return ONLY valid JSON. No markdown, no explanation.

User's description:
{description}

Scraped website content:
Title: {site_title}
Headings:
{site_headings}

Body summary:
{site_summary}
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                print(colored(f"[-] Failed to parse website enrichment JSON", "red"))
                result = enrich_campaign_description(description)
                result["website_url"] = website_data.get("url", "")
                return result
        else:
            result = enrich_campaign_description(description)
            result["website_url"] = website_data.get("url", "")
            return result

    required_keys = ["refined_name", "keywords", "competitor_keywords", "target_audience", "intent_queries", "pain_points", "steal_audience_angle"]
    for key in required_keys:
        if key not in result:
            result[key] = _default_for_key(key, description)

    result["website_url"] = website_data.get("url", "")
    return result


def analyze_competitor(competitor_name: str, niche_description: str) -> dict:
    prompt = f"""
You are a competitive intelligence analyst. Given a competitor name/brand and a niche description, analyze their likely social media strategy.

Return a JSON object with:
1. "likely_platforms": Array of platforms they likely focus on
2. "content_strategy": 2-3 sentence description of their likely content approach
3. "audience_overlap": 2-3 sentence on how much their audience overlaps with the user's target
4. "steal_play": 2-3 sentence specific tactic to steal their audience
5. "viral_formats": Array of 2-3 content formats that likely work for them
6. "estimated_reach": Estimate of their social reach (Low/Medium/High/Very High)

Competitor: {competitor_name}
Niche: {niche_description}

Return ONLY valid JSON. No markdown.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {"likely_platforms": ["twitter"], "content_strategy": "Unknown", "audience_overlap": "Unknown", "steal_play": "Unknown", "viral_formats": [], "estimated_reach": "Unknown"}


def analyze_viral_post(post_text: str, campaign_description: str) -> dict:
    prompt = f"""
You are a viral content strategist and copywriter. Given a social media post and a campaign description, analyze it AND write an improved version.

Return a JSON object with:
1. "viral_hook": What makes the opening/presentation effective (1-2 sentences)
2. "emotional_triggers": Array of emotional triggers this post hits
3. "replication_angle": How the user could create a similar post for their offering (2-3 sentences)
4. "suggested_reply": A 1-2 sentence reply the user could post to engage with this thread
5. "format": The content format (question, story, list, tutorial, opinion, etc.)
6. "improved_version": A rewritten, more engaging version of the original post that stays true to the core message but improves hook, clarity, and engagement potential. Keep the same length or slightly shorter.

Post text:
{post_text}

Campaign: {campaign_description}

Return ONLY valid JSON. No markdown.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {"viral_hook": "Unknown", "emotional_triggers": [], "replication_angle": "Unknown", "suggested_reply": "", "format": "Unknown"}


def generate_lead_keywords(campaign: dict) -> list[str]:
    name = campaign.get("name", "")
    desc = campaign.get("description", "")[:500]
    keywords = campaign.get("keywords", [])
    competitors = campaign.get("competitor_keywords", [])
    intent_q = campaign.get("intent_queries", [])
    pain_points = campaign.get("pain_points", [])
    audience = campaign.get("target_audience", "")
    value_prop = campaign.get("value_proposition", "")
    viral_angles = campaign.get("viral_content_angles", [])
    competitor_names = [c.get("name", "") for c in campaign.get("competitors", [])]

    prompt = f"""
You are a social media lead generation strategist. Given a full campaign profile, generate 10 optimized search queries to find people who are actively looking for this solution or showing buying intent.

These queries should be realistic social media searches that surface:
- People asking for recommendations
- People complaining about problems this solves
- People comparing options in this space
- People who just signed up for similar services
- People looking for alternatives to competitor tools

Campaign name: {name}
Description: {desc}
Target audience: {audience}
Value proposition: {value_prop}
Keywords: {', '.join(keywords[:8])}
Competitor keywords: {', '.join(competitors[:5])}
Intent queries: {', '.join(intent_q[:5])}
Pain points: {', '.join(pain_points[:5])}
Viral content angles: {', '.join(viral_angles[:3])}
Tracked competitors: {', '.join(competitor_names[:5])}

Return ONLY a JSON array of 10 search query strings. No markdown.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return [q for q in result if q.strip()][:10]
    except json.JSONDecodeError:
        pass

    return (keywords + intent_q + [desc])[:6]


def generate_engagement_keywords(campaign: dict) -> list[str]:
    name = campaign.get("name", "")
    desc = campaign.get("description", "")[:500]
    value_prop = campaign.get("value_proposition", "")
    pain_points = campaign.get("pain_points", [])
    viral_angles = campaign.get("viral_content_angles", [])
    steal_angle = campaign.get("steal_audience_angle", "")

    prompt = f"""
You are a social media engagement strategist. Given a campaign profile, generate 10 optimized search queries to find posts, threads, and conversations where the user can add value and build relationships.

These queries should surface:
- Discussions where offering advice or insights would attract potential leads
- Posts from people in the target audience asking thoughtful questions
- Trending conversations in the niche where visibility would help
- Posts from competitors' customers or followers who are dissatisfied
- Community threads where the user can position themselves as helpful

The goal is NOT to find leads directly, but to find conversations where thoughtful engagement builds authority.

Campaign name: {name}
Description: {desc}
Value proposition: {value_prop}
Pain points: {', '.join(pain_points[:5])}
Viral content angles: {', '.join(viral_angles[:3])}
Audience capture strategy: {steal_angle}

Return ONLY a JSON array of 10 search query strings. No markdown.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return [q for q in result if q.strip()][:10]
    except json.JSONDecodeError:
        pass

    return [f"{name} tips", f"{name} advice", "help with " + name]


def generate_synthetic_leads(campaign: dict, mode: str = "leads", count: int = 10) -> list[dict]:
    name = campaign.get("name", "")
    desc = campaign.get("description", "")[:500]
    keywords = campaign.get("keywords", [])
    competitors = campaign.get("competitor_keywords", [])
    pain_points = campaign.get("pain_points", [])
    audience = campaign.get("target_audience", "")
    value_prop = campaign.get("value_proposition", "")

    if mode == "engagement":
        instruction = """
Each entry represents a social media post or thread where someone is asking for advice, sharing a problem, or discussing the niche. The goal is to find conversations the user can join to add value and build relationships.

For each entry include:
- "username": a realistic handle
- "display_name": a realistic name
- "post_text": a realistic social media post or question related to the campaign
- "follower_count": realistic number
- "post_url": a placeholder URL
- "bio": short bio
- "avatar_url": empty string
- "platform": "twitter"
- "id": a uuid-like string
- "intent_score": 0 (not a lead, just a conversation)
- "lead_type": "conversation"
"""
    else:
        instruction = """
Each entry represents a person who is actively looking for a solution like this or showing buying intent.

For each entry include:
- "username": a realistic handle
- "display_name": a realistic name
- "post_text": a realistic social media post showing need, pain, or buying intent
- "follower_count": realistic number
- "post_url": a placeholder URL
- "bio": short bio showing relevance
- "avatar_url": empty string
- "platform": "twitter"
- "id": a uuid-like string
- "intent_score": a number from 1-10 indicating buying intent
- "lead_type": "lead"
"""

    prompt = f"""
You are a social media lead generation simulation engine. Given a campaign profile, generate {count} realistic social media entries.

Campaign name: {name}
Description: {desc}
Target audience: {audience}
Value proposition: {value_prop}
Keywords: {', '.join(keywords[:6])}
Competitors: {', '.join(competitors[:4])}
Pain points: {', '.join(pain_points[:4])}

{instruction}

Return ONLY a JSON array of {count} objects. Each object must have all the fields listed above.
No markdown, no explanation.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result[:count]
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result[:count]
            except json.JSONDecodeError:
                pass

    # Hard fallback
    fallback = []
    for i in range(min(count, 5)):
        fallback.append({
            "id": f"gpt-fallback-{i}",
            "platform": "twitter",
            "username": f"user_{i}",
            "display_name": f"Potential Lead {i+1}",
            "post_text": f"Looking for a solution to help with {keywords[0] if keywords else name}",
            "follower_count": 100 + i * 50,
            "bio": f"Interested in {name}",
            "post_url": "",
            "avatar_url": "",
            "intent_score": 7 - i,
            "lead_type": "lead",
        })
    return fallback


def qualify_search_results(posts: list[dict], campaign: dict) -> list[dict]:
    if not posts:
        return []

    campaign_context = f"""
Campaign: {campaign.get('name', '')}
Description: {campaign.get('description', '')[:300]}
Target audience: {campaign.get('target_audience', '')}
Value proposition: {campaign.get('value_proposition', '')}
Pain points: {', '.join(campaign.get('pain_points', [])[:4])}
"""

    post_summaries = []
    for i, p in enumerate(posts):
        post_summaries.append(f"[{i}] User: {p.get('username', '')} | Text: {p.get('post_text', '')[:200]} | Followers: {p.get('follower_count', 'N/A')}")

    prompt = f"""
You are a lead qualification analyst. Given a campaign and a list of social media posts/profiles, score each one from 1-10 on how good of a lead they are.

Scoring criteria:
- 9-10: Perfect fit — actively asking for this exact solution, high intent
- 7-8: Strong fit — clearly in the target audience, showing interest or pain
- 5-6: Moderate fit — related topic but not explicitly looking
- 3-4: Weak fit — loosely related, may need nurturing
- 1-2: Not a fit — unrelated or competitor

Also classify each as one of: "hot_lead", "warm_lead", "cold_lead", "conversation", "not_relevant"

{campaign_context}

Posts to score:
{chr(10).join(post_summaries)}

Return ONLY a JSON array of objects, one per post, with:
- "index": the post index
- "score": 1-10
- "classification": one of the above
- "reason": 1 sentence explaining the score

No markdown, no explanation.
""".strip()

    raw = generate_response(prompt, AI_MODEL)
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return [{"index": i, "score": 5, "classification": "warm_lead", "reason": "Unable to qualify"} for i in range(len(posts))]


def _fallback_enrichment(description: str) -> dict:
    return {
        "refined_name": description.split(".")[0][:50],
        "keywords": [description],
        "competitor_keywords": [],
        "target_audience": f"People interested in {description}",
        "intent_queries": [f"I need {description}"],
        "pain_points": ["Unknown - refine with AI"],
        "steal_audience_angle": "Analyze competitor followers and engage with relevant content."
    }


def _default_for_key(key: str, description: str):
    defaults = {
        "refined_name": description[:50],
        "keywords": [description],
        "competitor_keywords": [],
        "target_audience": f"People interested in {description}",
        "intent_queries": [f"I need {description}"],
        "pain_points": ["Unknown"],
        "steal_audience_angle": "Analyze competitor followers and engage with relevant content."
    }
    return defaults.get(key, "")
