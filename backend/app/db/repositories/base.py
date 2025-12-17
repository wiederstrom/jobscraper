"""
Base repository pattern for database operations
Provides common CRUD operations for all repositories
"""

from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Base

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common database operations.

    Usage:
        class JobRepository(BaseRepository[Job]):
            def __init__(self, db: Session):
                super().__init__(Job, db)
    """

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """Update an existing record"""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:
        """Delete a record by ID"""
        obj = self.get_by_id(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

    def count(self) -> int:
        """Count total records"""
        return self.db.query(self.model).count()

    def exists(self, **filters) -> bool:
        """Check if record exists with given filters"""
        query = self.db.query(self.model)
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.first() is not None

    def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """Get a single record by any field"""
        if hasattr(self.model, field_name):
            return self.db.query(self.model).filter(
                getattr(self.model, field_name) == value
            ).first()
        return None

    def get_multi_by_field(
        self, field_name: str, value: Any, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records by field value"""
        if hasattr(self.model, field_name):
            return (
                self.db.query(self.model)
                .filter(getattr(self.model, field_name) == value)
                .offset(skip)
                .limit(limit)
                .all()
            )
        return []
