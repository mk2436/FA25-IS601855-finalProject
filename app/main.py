"""
FastAPI Main Application Module

This module defines the main FastAPI application, including:
- Application initialization and configuration
- API endpoints for user authentication
- API endpoints for calculation management (BREAD operations)
- Web routes for HTML templates
- Database table creation on startup

The application follows a RESTful API design with proper separation of concerns:
- Routes handle HTTP requests and responses
- Models define database structure
- Schemas validate request/response data
- Dependencies handle authentication and database sessions
"""

from contextlib import asynccontextmanager  # Used for startup/shutdown events
from datetime import datetime, timezone, timedelta
from uuid import UUID  # For type validation of UUIDs in path parameters
from typing import List

# FastAPI imports
from fastapi import Body, FastAPI, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles  # For serving static files (CSS, JS)
from fastapi.templating import Jinja2Templates  # For HTML templates

from sqlalchemy.orm import Session  # SQLAlchemy database session
from sqlalchemy import func  # For aggregate functions

import uvicorn  # ASGI server for running FastAPI apps
import os
import shutil
from pathlib import Path

# Application imports
from app.auth.dependencies import get_current_active_user, get_current_active_user_db  # Authentication dependency
from app.models.calculation import Calculation  # Database model for calculations
from app.models.user import User  # Database model for users
from app.schemas.calculation import CalculationBase, CalculationResponse, CalculationUpdate, CalculationStats  # API request/response schemas
from app.schemas.token import TokenResponse  # API token schema
from app.schemas.user import UserCreate, UserResponse, UserLogin, UserUpdate, PasswordUpdate  # User schemas
from app.database import Base, get_db, engine  # Database connection


# ------------------------------------------------------------------------------
# Create tables on startup using the lifespan event
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    
    This runs when the application starts and creates all database tables
    defined in SQLAlchemy models. It's an alternative to using Alembic
    for simpler applications.
    
    Args:
        app: FastAPI application instance
    """
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    yield  # This is where application runs
    # Cleanup code would go here (after yield), but we don't need any

# Initialize the FastAPI application with metadata and lifespan
app = FastAPI(
    title="Calculations API",
    description="API for managing calculations",
    version="1.0.0",
    lifespan=lifespan  # Pass our lifespan context manager
)

# ------------------------------------------------------------------------------
# Static Files and Templates Configuration
# ------------------------------------------------------------------------------
# Mount the static files directory for serving CSS, JS, and images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates directory for HTML rendering
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------------------------
# Web (HTML) Routes
# ------------------------------------------------------------------------------
# Our web routes use HTML responses with Jinja2 templates
# These provide a user-friendly web interface alongside the API

@app.get("/", response_class=HTMLResponse, tags=["web"])
def read_index(request: Request):
    """
    Landing page.
    
    Displays the welcome page with links to register and login.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse, tags=["web"])
def login_page(request: Request):
    """
    Login page.
    
    Displays a form for users to enter credentials and log in.
    """
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse, tags=["web"])
def register_page(request: Request):
    """
    Registration page.
    
    Displays a form for new users to create an account.
    """
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse, tags=["web"])
def dashboard_page(request: Request):
    """
    Dashboard page, listing calculations & new calculation form.
    
    This is the main interface after login, where users can:
    - See all their calculations
    - Create a new calculation
    - Access links to view/edit/delete calculations
    
    JavaScript in this page calls the API endpoints to fetch and display data.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard/view/{calc_id}", response_class=HTMLResponse, tags=["web"])
def view_calculation_page(request: Request, calc_id: str):
    """
    Page for viewing a single calculation (Read).
    
    Part of the BREAD (Browse, Read, Edit, Add, Delete) pattern:
    - This is the Read page
    
    Args:
        request: The FastAPI request object (required by Jinja2)
        calc_id: UUID of the calculation to view
        
    Returns:
        HTMLResponse: Rendered template with calculation ID passed to frontend
    """
    return templates.TemplateResponse("view_calculation.html", {"request": request, "calc_id": calc_id})

@app.get("/dashboard/edit/{calc_id}", response_class=HTMLResponse, tags=["web"])
def edit_calculation_page(request: Request, calc_id: str):
    """
    Page for editing a calculation (Update).
    
    Part of the BREAD (Browse, Read, Edit, Add, Delete) pattern:
    - This is the Edit page
    
    Args:
        request: The FastAPI request object (required by Jinja2)
        calc_id: UUID of the calculation to edit
        
    Returns:
        HTMLResponse: Rendered template with calculation ID passed to frontend
    """
    return templates.TemplateResponse("edit_calculation.html", {"request": request, "calc_id": calc_id})

@app.get("/profile", response_class=HTMLResponse, tags=["web"])
def profile_page(request: Request):
    """
    User profile settings page.
    
    Displays a form for users to update their profile information
    and manage their profile picture.
    """
    return templates.TemplateResponse("profile.html", {"request": request})


# ------------------------------------------------------------------------------
# Health Endpoint
# ------------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def read_health():
    """Health check."""
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# User Registration Endpoint
# ------------------------------------------------------------------------------
@app.post(
    "/auth/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["auth"]
)
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.
    """
    user_data = user_create.dict(exclude={"confirm_password"})
    try:
        user = User.register(db, user_data)
        db.commit()
        db.refresh(user)
        return user
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ------------------------------------------------------------------------------
# User Login Endpoints
# ------------------------------------------------------------------------------
@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Login with JSON payload (username & password).
    Returns an access token, refresh token, and user info.
    """
    auth_result = User.authenticate(db, user_login.username, user_login.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_result["user"]
    db.commit()  # commit the last_login update

    # Ensure expires_at is timezone-aware
    expires_at = auth_result.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    return TokenResponse(
        access_token=auth_result["access_token"],
        refresh_token=auth_result["refresh_token"],
        token_type="bearer",
        expires_at=expires_at,
        user_id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        profile_picture=user.profile_picture,
        is_active=user.is_active,
        is_verified=user.is_verified
    )

@app.post("/auth/token", tags=["auth"])
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login with form data (Swagger/UI).
    Returns an access token.
    """
    auth_result = User.authenticate(db, form_data.username, form_data.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": auth_result["access_token"],
        "token_type": "bearer"
    }


# ------------------------------------------------------------------------------
# Calculations Endpoints (BREAD)
# ------------------------------------------------------------------------------
# Create (Add) Calculation
@app.post(
    "/calculations",
    response_model=CalculationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["calculations"],
)
def create_calculation(
    calculation_data: CalculationBase,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new calculation for the authenticated user.
    Automatically computes the 'result'.
    """
    try:
        new_calculation = Calculation.create(
            calculation_type=calculation_data.type,
            user_id=current_user.id,
            inputs=calculation_data.inputs,
        )
        new_calculation.result = new_calculation.get_result()

        db.add(new_calculation)
        db.commit()
        db.refresh(new_calculation)
        return new_calculation

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Browse / List Calculations
@app.get("/calculations", response_model=List[CalculationResponse], tags=["calculations"])
def list_calculations(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all calculations belonging to the current authenticated user.
    """
    calculations = db.query(Calculation).filter(Calculation.user_id == current_user.id).all()
    return calculations


# Statistics Endpoint (must come before /calculations/{calc_id} to avoid route conflicts)
@app.get("/calculations/stats", response_model=CalculationStats, tags=["calculations"])
def get_calculation_stats(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics and summaries for the current authenticated user's calculations.
    Returns metrics such as total calculations, average operands, most used operation, etc.
    """
    try:
        # Get all calculations for the user
        calculations = db.query(Calculation).filter(Calculation.user_id == current_user.id).all()
        
        if not calculations:
            # Return empty stats if no calculations exist
            return CalculationStats(
                total_calculations=0,
                average_operands=0.0,
                most_used_operation=None,
                operations_by_type={},
                average_result=None,
                first_calculation_date=None,
                last_calculation_date=None,
                total_operands=0
            )
        
        # Calculate statistics
        total_calculations = len(calculations)
        
        # Count operands and operations by type
        total_operands = 0
        operations_by_type = {}
        results = []
        
        for calc in calculations:
            # Count operands
            if isinstance(calc.inputs, list):
                total_operands += len(calc.inputs)
            
            # Count by operation type
            op_type = calc.type.lower()
            operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1
            
            # Collect results for average
            if calc.result is not None:
                results.append(calc.result)
        
        # Calculate average operands
        average_operands = total_operands / total_calculations if total_calculations > 0 else 0.0
        
        # Find most used operation
        most_used_operation = max(operations_by_type.items(), key=lambda x: x[1])[0] if operations_by_type else None
        
        # Calculate average result
        average_result = sum(results) / len(results) if results else None
        
        # Find first and last calculation dates
        dates = [calc.created_at for calc in calculations if calc.created_at]
        first_calculation_date = min(dates) if dates else None
        last_calculation_date = max(dates) if dates else None
        
        # Round values properly
        avg_operands_rounded = round(float(average_operands), 2)
        avg_result_rounded = round(float(average_result), 2) if average_result is not None else None
        
        return CalculationStats(
            total_calculations=total_calculations,
            average_operands=avg_operands_rounded,
            most_used_operation=most_used_operation,
            operations_by_type=operations_by_type,
            average_result=avg_result_rounded,
            first_calculation_date=first_calculation_date,
            last_calculation_date=last_calculation_date,
            total_operands=total_operands
        )
    except Exception as e:
        # Log the error and return a proper error response
        import traceback
        print(f"Error in get_calculation_stats: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate statistics: {str(e)}"
        )


# Read / Retrieve a Specific Calculation by ID
@app.get("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def get_calculation(
    calc_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve a single calculation by its UUID, if it belongs to the current user.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    return calculation


# Edit / Update a Calculation
@app.put("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def update_calculation(
    calc_id: str,
    calculation_update: CalculationUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update the inputs (and thus the result) of a specific calculation.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    if calculation_update.inputs is not None:
        calculation.inputs = calculation_update.inputs
        calculation.result = calculation.get_result()

    calculation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calculation)
    return calculation


# Delete a Calculation
@app.delete("/calculations/{calc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["calculations"])
def delete_calculation(
    calc_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a calculation by its UUID, if it belongs to the current user.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    db.delete(calculation)
    db.commit()
    return None


# ------------------------------------------------------------------------------
# User Profile Endpoints
# ------------------------------------------------------------------------------
@app.get("/users/me", response_model=UserResponse, tags=["users"])
def get_current_user_profile(
    current_user_response = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the current authenticated user's profile information.
    Fetches the user from the database to get the latest profile information including profile_picture.
    """
    # Fetch the actual user from the database to get the latest data
    user = db.query(User).filter(User.id == current_user_response.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@app.put("/users/me", response_model=UserResponse, tags=["users"])
def update_current_user_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_active_user_db),
    db: Session = Depends(get_db)
):
    """
    Update the current authenticated user's profile information.
    """
    # Check if email or username is being changed and if it's already taken
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
    
    if user_update.username and user_update.username != current_user.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already in use"
            )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/users/profile-picture", response_model=UserResponse, tags=["users"])
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user = Depends(get_current_active_user_db),
    db: Session = Depends(get_db)
):
    """
    Upload a profile picture for the current authenticated user.
    Accepts image files (JPEG, PNG, GIF, WebP) up to 5MB.
    """
    try:
        # Validate file type
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ""
        
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Validate file size (5MB limit)
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 5MB limit"
            )
        
        # Create uploads directory if it doesn't exist
        try:
            upload_dir = Path("static/uploads/profile_pictures")
            upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create upload directory: {str(e)}"
            )
        
        # Generate unique filename using user ID
        filename = f"user_{current_user.id}{file_ext}"
        file_path = upload_dir / filename
        
        # Delete old profile picture if it exists
        if current_user.profile_picture:
            try:
                old_file_path = Path("static") / current_user.profile_picture.lstrip("/")
                if old_file_path.exists() and old_file_path.is_file():
                    old_file_path.unlink()
            except Exception:
                pass  # Ignore errors when deleting old file
        
        # Save the new file
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(contents)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
        
        # Update user's profile_picture field
        try:
            profile_picture_path = f"/static/uploads/profile_pictures/{filename}"
            current_user.profile_picture = profile_picture_path
            current_user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(current_user)
        except Exception as e:
            db.rollback()
            # Try to delete the uploaded file if database update fails
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update user profile: {str(e)}"
            )
        
        return current_user
        
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        # Catch any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@app.delete("/users/profile-picture", response_model=UserResponse, tags=["users"])
def delete_profile_picture(
    current_user = Depends(get_current_active_user_db),
    db: Session = Depends(get_db)
):
    """
    Delete the current authenticated user's profile picture.
    """
    if current_user.profile_picture:
        # Delete the file
        file_path = Path("static") / current_user.profile_picture.lstrip("/")
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
            except Exception:
                pass  # Ignore errors when deleting file
        
        # Clear the profile_picture field
        current_user.profile_picture = None
        current_user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(current_user)
    
    return current_user


@app.put("/users/password", status_code=status.HTTP_200_OK, tags=["users"])
def update_password(
    password_update: PasswordUpdate,
    current_user = Depends(get_current_active_user_db),
    db: Session = Depends(get_db)
):
    """
    Update the current authenticated user's password.
    Requires current password for verification.
    After successful update, user should be logged out for security.
    """
    # Verify current password
    if not current_user.verify_password(password_update.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash and update the new password
    try:
        hashed_password = User.hash_password(password_update.new_password)
        current_user.password = hashed_password
        current_user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "Password updated successfully. Please log in again with your new password.",
            "logout_required": True
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )


# ------------------------------------------------------------------------------
# Main Block to Run the Server
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="info")
