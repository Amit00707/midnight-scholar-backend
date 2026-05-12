from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Classroom
class ClassroomCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ClassroomResponse(ClassroomCreate):
    id: int
    teacher_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Enrollment
class StudentEnrollmentCreate(BaseModel):
    student_id: int

class StudentEnrollmentResponse(BaseModel):
    id: int
    class_id: int
    student_id: int
    enrolled_at: datetime

    class Config:
        from_attributes = True


# Assignment
class AssignmentCreate(BaseModel):
    book_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class AssignmentResponse(AssignmentCreate):
    id: int
    class_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Announcement
class AnnouncementCreate(BaseModel):
    title: str
    content: str

class AnnouncementResponse(AnnouncementCreate):
    id: int
    class_id: int
    created_at: datetime

    class Config:
        from_attributes = True
