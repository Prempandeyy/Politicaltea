from backend.database import SessionLocal, engine, Base
from backend.models import State, Topic, Post, Video, News


# Create tables
Base.metadata.create_all(bind=engine)


db = SessionLocal()


# =========================================
# STATES
# =========================================

states_data = [
    "Uttar Pradesh",
    "Delhi",
    "Maharashtra",
    "Rajasthan",
    "Bihar",
    "Jharkhand",
    "Madhya Pradesh",
    "West Bengal",
    "Tamil Nadu",
    "Karnataka",
    "Gujarat",
    "Haryana"
]


# =========================================
# CREATE STATES
# =========================================

for state_name in states_data:

    existing_state = db.query(State).filter(
        State.name == state_name
    ).first()

    if not existing_state:

        state = State(
            name=state_name
        )

        db.add(state)


db.commit()


# =========================================
# GET STATE IDs
# =========================================

states = {
    state.name: state.id
    for state in db.query(State).all()
}


# =========================================
# TOPICS
# =========================================

topics_data = [

    # Uttar Pradesh
    {
        "state": "Uttar Pradesh",
        "title": "Reservation Reform",
        "mentions": "4.8K conversations",
        "change": "+38%"
    },

    {
        "state": "Uttar Pradesh",
        "title": "State Budget",
        "mentions": "3.2K conversations",
        "change": "+26%"
    },

    {
        "state": "Uttar Pradesh",
        "title": "Student Politics",
        "mentions": "2.7K conversations",
        "change": "+21%"
    },


    # Delhi
    {
        "state": "Delhi",
        "title": "Delhi Development",
        "mentions": "5.1K conversations",
        "change": "+41%"
    },

    {
        "state": "Delhi",
        "title": "Pollution & Environment",
        "mentions": "3.9K conversations",
        "change": "+29%"
    },

    {
        "state": "Delhi",
        "title": "Jobs & Employment",
        "mentions": "3.1K conversations",
        "change": "+23%"
    },


    # Maharashtra
    {
        "state": "Maharashtra",
        "title": "Urban Development",
        "mentions": "4.2K conversations",
        "change": "+31%"
    },

    {
        "state": "Maharashtra",
        "title": "Farmers' Issues",
        "mentions": "3.7K conversations",
        "change": "+27%"
    },

    {
        "state": "Maharashtra",
        "title": "Mumbai Infrastructure",
        "mentions": "3.0K conversations",
        "change": "+19%"
    },


    # Rajasthan
    {
        "state": "Rajasthan",
        "title": "Water Crisis",
        "mentions": "3.8K conversations",
        "change": "+34%"
    },

    {
        "state": "Rajasthan",
        "title": "Education Reform",
        "mentions": "2.9K conversations",
        "change": "+22%"
    },

    {
        "state": "Rajasthan",
        "title": "Tourism Development",
        "mentions": "2.4K conversations",
        "change": "+17%"
    }
]


for item in topics_data:

    state_id = states[item["state"]]

    exists = db.query(Topic).filter(
        Topic.state_id == state_id,
        Topic.title == item["title"]
    ).first()

    if not exists:

        topic = Topic(
            title=item["title"],
            mentions=item["mentions"],
            change=item["change"],
            state_id=state_id
        )

        db.add(topic)


# =========================================
# POSTS
# =========================================

posts_data = [

    {
        "state": "Uttar Pradesh",
        "author": "Public Pulse UP",
        "avatar": "P",
        "type": "Analysis",
        "title": "What people in UP are talking about today",
        "body": "Jobs, education, development and reservation remain some of the biggest topics in today's political conversation.",
        "image": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1200&q=80"
    },

    {
        "state": "Uttar Pradesh",
        "author": "Ground Report",
        "avatar": "G",
        "type": "Opinion",
        "title": "A different conversation around reservation",
        "body": "The reservation debate is once again generating conversations around opportunity, access and possible reforms.",
        "image": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80"
    },

    {
        "state": "Delhi",
        "author": "Delhi Decode",
        "avatar": "D",
        "type": "Analysis",
        "title": "What is dominating Delhi's political conversation?",
        "body": "Development, pollution, employment and civic infrastructure are among the topics people are discussing.",
        "image": "https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=1200&q=80"
    },

    {
        "state": "Maharashtra",
        "author": "Mumbai Ground",
        "avatar": "M",
        "type": "Ground Report",
        "title": "Mumbai's biggest political conversations today",
        "body": "Infrastructure, urban development and local issues are driving conversations across the state.",
        "image": "https://images.unsplash.com/photo-1504711331083-9c6d3c6e5f44?auto=format&fit=crop&w=1200&q=80"
    },

    {
        "state": "Rajasthan",
        "author": "Rajasthan Pulse",
        "avatar": "R",
        "type": "Opinion",
        "title": "What Rajasthan is talking about today",
        "body": "Water, education and tourism development are among the biggest conversations across the state.",
        "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80"
    }
]


for item in posts_data:

    state_id = states[item["state"]]

    exists = db.query(Post).filter(
        Post.state_id == state_id,
        Post.title == item["title"]
    ).first()

    if not exists:

        post = Post(
            author=item["author"],
            avatar=item["avatar"],
            type=item["type"],
            title=item["title"],
            body=item["body"],
            image=item["image"],
            likes=0,
            state_id=state_id
        )

        db.add(post)


# =========================================
# VIDEOS
# =========================================

videos_data = [

    {
        "state": "Uttar Pradesh",
        "creator": "Awadh Talks",
        "title": "What's happening on the ground in UP?",
        "views": "82K views",
        "image": "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?auto=format&fit=crop&w=900&q=80"
    },

    {
        "state": "Delhi",
        "creator": "Delhi Decode",
        "title": "Delhi's biggest political conversations",
        "views": "71K views",
        "image": "https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=900&q=80"
    },

    {
        "state": "Maharashtra",
        "creator": "Mumbai Ground",
        "title": "What Mumbai is talking about today",
        "views": "64K views",
        "image": "https://images.unsplash.com/photo-1504711331083-9c6d3c6e5f44?auto=format&fit=crop&w=900&q=80"
    },

    {
        "state": "Rajasthan",
        "creator": "Rajasthan Pulse",
        "title": "Inside Rajasthan's latest political conversation",
        "views": "52K views",
        "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=80"
    }
]


for item in videos_data:

    state_id = states[item["state"]]

    exists = db.query(Video).filter(
        Video.state_id == state_id,
        Video.title == item["title"]
    ).first()

    if not exists:

        video = Video(
            creator=item["creator"],
            title=item["title"],
            views=item["views"],
            image=item["image"],
            state_id=state_id
        )

        db.add(video)


# =========================================
# NEWS
# =========================================

news_data = [

    {
        "state": "Uttar Pradesh",
        "source": "UP STATE DESK",
        "title": "Political developments dominate today's UP conversation",
        "time": "28 min ago",
        "image": "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=400&q=80"
    },

    {
        "state": "Uttar Pradesh",
        "source": "GROUND REPORT",
        "title": "New announcements spark discussion across UP",
        "time": "1 hr ago",
        "image": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=400&q=80"
    },

    {
        "state": "Delhi",
        "source": "DELHI DESK",
        "title": "Civic development becomes a major talking point",
        "time": "32 min ago",
        "image": "https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=400&q=80"
    },

    {
        "state": "Maharashtra",
        "source": "MUMBAI DESK",
        "title": "Infrastructure discussions dominate today's headlines",
        "time": "45 min ago",
        "image": "https://images.unsplash.com/photo-1504711331083-9c6d3c6e5f44?auto=format&fit=crop&w=400&q=80"
    },

    {
        "state": "Rajasthan",
        "source": "RAJASTHAN DESK",
        "title": "Water and development remain key conversations",
        "time": "1 hr ago",
        "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=400&q=80"
    }
]


for item in news_data:

    state_id = states[item["state"]]

    exists = db.query(News).filter(
        News.state_id == state_id,
        News.title == item["title"]
    ).first()

    if not exists:

        news = News(
            source=item["source"],
            title=item["title"],
            time=item["time"],
            image=item["image"],
            state_id=state_id
        )

        db.add(news)


# =========================================
# SAVE
# =========================================

db.commit()

db.close()


print("===================================")
print("Political Tea database seeded!")
print("===================================")
print(f"States: {len(states)}")
print("Topics, posts, videos and news added.")
print("===================================")