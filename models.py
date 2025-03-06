from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Date
from database import Base
from sqlalchemy.orm import relationship
from datetime import timedelta, date


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    apprentices = relationship("Apprentice", back_populates="creator")


class Apprentice(Base):
    __tablename__ = "apprentices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String)
    age = Column(Integer)
    cohort_year = Column(Integer)
    job_role = Column(String)
    skills = Column(String)
    creator_id = Column(Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates="apprentices")
    reviews = relationship("Review", back_populates="apprentice")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    apprentice_id = Column(Integer, ForeignKey("apprentices.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date_of_review = Column(Date)
    progress_review_form = Column(String, nullable=True)
    completed = Column(Boolean, default=False)

    apprentice = relationship("Apprentice", back_populates="reviews")
    user = relationship("User")

    @property
    def date_of_next_review(self):
        if self.date_of_review:
            return self.date_of_review + timedelta(weeks=10)
        return None
