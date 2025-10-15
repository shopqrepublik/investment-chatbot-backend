# app/crud.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid
from app.database import UserProfile, Portfolio, PortfolioAsset

def save_portfolio(
    db: Session, 
    user_id: str, 
    profile: Dict[str, Any], 
    portfolio_result: Dict[str, Any]
) -> str:
    """Save portfolio to database"""
    try:
        # Create portfolio record
        portfolio = Portfolio(
            user_id=user_id,
            profile_data=json.dumps(profile),
            portfolio_data=json.dumps(portfolio_result),
            created_at=datetime.now()
        )
        
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
        
        # Save portfolio assets
        portfolio_assets = portfolio_result.get('portfolio', [])
        for asset_data in portfolio_assets:
            asset = PortfolioAsset(
                portfolio_id=portfolio.id,
                ticker=asset_data.get('ticker', ''),
                name=asset_data.get('name', ''),
                weight=asset_data.get('weight', 0.0),
                asset_type=asset_data.get('asset_type', 'Stock'),
                sector=asset_data.get('sector', ''),
                current_price=asset_data.get('current_price', 0.0),
                target_price=asset_data.get('target_price', 0.0),
                allocation_percent=asset_data.get('allocation_percent', 0.0),
                expected_return=asset_data.get('expected_return', 0.0)
            )
            db.add(asset)
        
        db.commit()
        return str(portfolio.id)
        
    except Exception as e:
        db.rollback()
        raise e

def get_user_portfolios(db: Session, user_id: str) -> List[Dict[str, Any]]:
    """Get all portfolios for a user"""
    try:
        portfolios = db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc()).all()
        
        result = []
        for portfolio in portfolios:
            portfolio_data = json.loads(portfolio.portfolio_data)
            profile_data = json.loads(portfolio.profile_data)
            
            result.append({
                "portfolio_id": str(portfolio.id),
                "created_at": portfolio.created_at.isoformat(),
                "profile_summary": portfolio_data.get("profile_summary", {}),
                "portfolio_metrics": portfolio_data.get("portfolio_metrics", {}),
                "asset_count": len(portfolio_data.get("portfolio", [])),
                "investment_horizon": profile_data.get("investment_horizon", "6m"),
                "risk_tolerance": profile_data.get("risk_tolerance", "medium")
            })
        
        return result
        
    except Exception as e:
        print(f"Error getting user portfolios: {e}")
        return []

def get_portfolio_by_id(db: Session, portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get specific portfolio by ID"""
    try:
        portfolio = db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id
        ).first()
        
        if not portfolio:
            return None
        
        portfolio_data = json.loads(portfolio.portfolio_data)
        profile_data = json.loads(portfolio.profile_data)
        
        # Get portfolio assets
        assets = db.query(PortfolioAsset).filter(
            PortfolioAsset.portfolio_id == portfolio_id
        ).all()
        
        portfolio_assets = []
        for asset in assets:
            portfolio_assets.append({
                "ticker": asset.ticker,
                "name": asset.name,
                "weight": asset.weight,
                "asset_type": asset.asset_type,
                "sector": asset.sector,
                "current_price": asset.current_price,
                "target_price": asset.target_price,
                "allocation_percent": asset.allocation_percent,
                "expected_return": asset.expected_return
            })
        
        return {
            "portfolio_id": str(portfolio.id),
            "created_at": portfolio.created_at.isoformat(),
            "profile_data": profile_data,
            "portfolio": portfolio_assets,
            "asset_allocation": portfolio_data.get("asset_allocation", {}),
            "portfolio_metrics": portfolio_data.get("portfolio_metrics", {}),
            "recommendations": portfolio_data.get("recommendations", []),
            "profile_summary": portfolio_data.get("profile_summary", {})
        }
        
    except Exception as e:
        print(f"Error getting portfolio by ID: {e}")
        return None

def create_user(db: Session, email: str, username: str, password_hash: str) -> UserProfile:
    """Create new user"""
    try:
        user = UserProfile(
            email=email,
            username=username,
            password_hash=password_hash,
            created_at=datetime.now()
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
        
    except Exception as e:
        db.rollback()
        raise e

def get_user_by_email(db: Session, email: str) -> Optional[UserProfile]:
    """Get user by email"""
    return db.query(UserProfile).filter(UserProfile.email == email).first()

def get_user_by_id(db: Session, user_id: str) -> Optional[UserProfile]:
    """Get user by ID"""
    return db.query(UserProfile).filter(UserProfile.id == user_id).first()

def update_user_profile(db: Session, user_id: str, profile_data: Dict[str, Any]) -> bool:
    """Update user profile"""
    try:
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            return False
        
        user.profile_data = json.dumps(profile_data)
        user.updated_at = datetime.now()
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        return False

def delete_portfolio(db: Session, portfolio_id: str, user_id: str) -> bool:
    """Delete portfolio"""
    try:
        portfolio = db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id
        ).first()
        
        if not portfolio:
            return False
        
        # Delete associated assets
        db.query(PortfolioAsset).filter(
            PortfolioAsset.portfolio_id == portfolio_id
        ).delete()
        
        # Delete portfolio
        db.delete(portfolio)
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        return False