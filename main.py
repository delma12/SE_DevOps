import os
import shutil
from datetime import date, datetime
from typing import Annotated, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from models import Apprentice, Review, User

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="./static"), name="static")

load_dotenv()

init_db()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_admin_user(db: Session):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "defaultpassword")

    if not db.query(User).filter(User.username == admin_username).first():
        hashed_password = pwd_context.hash(admin_password)
        admin_user = User(
            username=admin_username, hashed_password=hashed_password, is_admin=True
        )
        db.add(admin_user)
        db.commit()


@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        create_admin_user(db)
    finally:
        db.close()


def get_current_user(username: str = Cookie(None), db: Session = Depends(get_db)):
    if not username:
        raise HTTPException(status_code=403, detail="User not authenticated")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def is_admin(user: User):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Unauthorised")


class UserCreate(BaseModel):
    username: Annotated[
        str, Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_-]+$")
    ]
    password: Annotated[str, Field(min_length=8, max_length=100)]
    is_admin: bool = False


class UserUpdate(BaseModel):
    username: Annotated[
        str, Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_-]+$")
    ]
    password: Annotated[str, Field(min_length=8, max_length=100)]
    is_admin: bool = False


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    class Config:
        orm_mode = True


class ApprenticeCreate(BaseModel):
    name: str
    email: str
    age: int
    cohort_year: int
    job_role: str
    skills: str


class ApprenticeUpdate(BaseModel):
    name: str
    email: str
    age: int
    cohort_year: int
    job_role: str
    skills: str


class ApprenticeResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int
    cohort_year: int
    job_role: str
    skills: str
    creator_username: str

    class Config:
        orm_mode = True


class ReviewCreate(BaseModel):
    content: str
    apprentice_id: int
    date_of_review: date
    completed: bool = False


class ReviewUpdate(BaseModel):
    content: str
    apprentice_id: int
    date_of_review: date
    completed: bool = False


class ReviewResponse(BaseModel):
    id: int
    content: str
    apprentice_id: int
    user_id: int
    date_of_review: date
    progress_review_form: Optional[str] = None
    completed: bool = False

    class Config:
        from_attributes = True


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/login", response_class=RedirectResponse)
async def login_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    user = db.query(User).filter(User.username == username).first()
    if user and pwd_context.verify(password, user.hashed_password):
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="username", value=username)
        return response
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/register")
async def register_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "message": "Registration successful! You can now log in."},
    )


@app.get("/dashboard")
async def dashboard(request: Request, user: UserResponse = Depends(get_current_user)):
    title = f"Welcome, {'Admin' if user.is_admin else user.username}'s Dashboard"
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": title, "is_admin": user.is_admin},
    )


@app.get("/users", response_model=List[UserResponse])
async def get_users(
    request: Request,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    # blocks all non-admin users
    is_admin(user)
    users = db.query(User).all()
    return templates.TemplateResponse(
        "users.html", {"request": request, "users": users, "is_admin": user.is_admin}
    )


@app.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    is_admin(current_user)
    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        is_admin=user_data.is_admin,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    is_admin(current_user)
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user_data.username
    if user_data.password:
        db_user.hashed_password = pwd_context.hash(user_data.password)
    db_user.is_admin = user_data.is_admin
    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/users/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    is_admin(current_user)
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return db_user


@app.get("/apprentices")
async def apprentices(
    request: Request,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    apprentices = db.query(Apprentice).all()
    return templates.TemplateResponse(
        "apprentice.html",
        {
            "request": request,
            "apprentices": apprentices,
            "is_admin": user.is_admin,
            "current_user": user,
        },
    )


@app.post("/apprentices", response_model=ApprenticeResponse)
async def create_apprentice(
    apprentice_data: ApprenticeCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    new_apprentice = Apprentice(
        name=apprentice_data.name,
        email=apprentice_data.email,
        age=apprentice_data.age,
        cohort_year=apprentice_data.cohort_year,
        job_role=apprentice_data.job_role,
        skills=apprentice_data.skills,
        creator_id=current_user.id,
    )
    db.add(new_apprentice)
    db.commit()
    db.refresh(new_apprentice)

    creator_username = (
        db.query(User.username).filter(User.id == current_user.id).scalar()
    )

    return ApprenticeResponse(
        id=new_apprentice.id,
        name=new_apprentice.name,
        email=new_apprentice.email,
        age=new_apprentice.age,
        cohort_year=new_apprentice.cohort_year,
        job_role=new_apprentice.job_role,
        skills=new_apprentice.skills,
        creator_username=creator_username,
    )


@app.get("/apprentices/{apprentice_id}", response_model=ApprenticeResponse)
async def get_apprentice(
    apprentice_id: int,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    apprentice = db.query(Apprentice).filter(Apprentice.id == apprentice_id).first()
    if not apprentice:
        raise HTTPException(status_code=404, detail="Apprentice not found")

    creator_username = (
        db.query(User.username).filter(User.id == apprentice.creator_id).scalar()
        or "Deleted User"
    )

    return ApprenticeResponse(
        id=apprentice.id,
        name=apprentice.name,
        email=apprentice.email,
        age=apprentice.age,
        cohort_year=apprentice.cohort_year,
        job_role=apprentice.job_role,
        skills=apprentice.skills,
        creator_username=creator_username,
    )


@app.put("/apprentices/{apprentice_id}", response_model=ApprenticeResponse)
async def update_apprentice(
    apprentice_id: int,
    apprentice_data: ApprenticeUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):

    db_apprentice = db.query(Apprentice).filter(Apprentice.id == apprentice_id).first()

    if not db_apprentice:
        raise HTTPException(status_code=404, detail="Apprentice not found")

    if is_admin(current_user):

        pass
    elif db_apprentice.creator_id != current_user.id:

        raise HTTPException(
            status_code=403, detail="Not authorised to edit this apprentice"
        )

    db_apprentice.name = apprentice_data.name
    db_apprentice.email = apprentice_data.email
    db_apprentice.age = apprentice_data.age
    db_apprentice.cohort_year = apprentice_data.cohort_year
    db_apprentice.job_role = apprentice_data.job_role
    db_apprentice.skills = apprentice_data.skills

    db.commit()
    db.refresh(db_apprentice)

    creator = db.query(User).filter(User.id == db_apprentice.creator_id).first()
    creator_username = creator.username if creator else "Deleted User"

    return ApprenticeResponse(
        id=db_apprentice.id,
        name=db_apprentice.name,
        email=db_apprentice.email,
        age=db_apprentice.age,
        cohort_year=db_apprentice.cohort_year,
        job_role=db_apprentice.job_role,
        skills=db_apprentice.skills,
        creator_username=creator_username,
    )


@app.delete("/apprentices/{apprentice_id}", response_model=ApprenticeResponse)
async def delete_apprentice(
    apprentice_id: int,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    is_admin(user)

    db_apprentice = db.query(Apprentice).filter(Apprentice.id == apprentice_id).first()
    if not db_apprentice:
        raise HTTPException(status_code=404, detail="Apprentice not found")

    creator = db.query(User).filter(User.id == db_apprentice.creator_id).first()

    creator_username = creator.username if creator else "Deleted User"

    response = ApprenticeResponse(
        id=db_apprentice.id,
        name=db_apprentice.name,
        email=db_apprentice.email,
        age=db_apprentice.age,
        cohort_year=db_apprentice.cohort_year,
        job_role=db_apprentice.job_role,
        skills=db_apprentice.skills,
        creator_username=creator_username,
    )

    db.delete(db_apprentice)
    db.commit()

    return response


@app.get("/reviews")
async def reviews(
    request: Request,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    reviews = db.query(Review).join(Review.apprentice).join(Review.user).all()
    apprentices = db.query(Apprentice).all()
    return templates.TemplateResponse(
        "reviews.html",
        {
            "request": request,
            "reviews": reviews,
            "apprentices": apprentices,
            "is_admin": user.is_admin,
            "current_user": user,
        },
    )


@app.post("/reviews", response_model=ReviewResponse)
async def create_review(
    apprentice_id: int = Form(...),
    content: str = Form(...),
    date_of_review: str = Form(...),
    completed: bool = Form(False),
    review_document: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    try:
        document_path = None
        if review_document:
            upload_dir = "uploads/reviews"
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{review_document.filename}"
            document_path = os.path.join(upload_dir, filename)

            with open(document_path, "wb") as buffer:
                shutil.copyfileobj(review_document.file, buffer)

        new_review = Review(
            content=content,
            apprentice_id=apprentice_id,
            user_id=current_user.id,
            date_of_review=datetime.strptime(date_of_review, "%Y-%m-%d").date(),
            progress_review_form=document_path,
            completed=completed,
        )

        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        return new_review

    except Exception as e:
        if document_path and os.path.exists(document_path):
            os.remove(document_path)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.put("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    apprentice_id: int = Form(...),
    content: str = Form(...),
    date_of_review: str = Form(...),
    completed: bool = Form(False),
    review_document: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    # Get existing review
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Check permissions
    if not current_user.is_admin and review.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorised to edit this review"
        )

    try:
        # Handle file upload if provided
        if review_document:
            # Delete old file if it exists
            if review.progress_review_form:
                try:
                    os.remove(review.progress_review_form)
                except OSError:
                    pass  # File might not exist

            # Save new file
            upload_dir = "uploads/reviews"
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{review_document.filename}"
            document_path = os.path.join(upload_dir, filename)

            with open(document_path, "wb") as buffer:
                shutil.copyfileobj(review_document.file, buffer)

            review.progress_review_form = document_path

        # Update review fields
        review.apprentice_id = apprentice_id
        review.content = content
        review.date_of_review = datetime.strptime(date_of_review, "%Y-%m-%d").date()
        review.completed = completed

        db.commit()
        db.refresh(review)
        return review

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/reviews/{review_id}")
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    if not user.is_admin:
        raise HTTPException(
            status_code=403, detail="Only administrators can delete reviews"
        )

    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    db.delete(review)
    db.commit()
    return {"message": "Review deleted successfully"}


@app.get("/logout")
async def logout(response: RedirectResponse):
    response.delete_cookie(key="username")
    return RedirectResponse(url="/")


if __name__ == "__main__":

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)


@app.head("/")
async def head_index():
    return Response(status_code=200)
