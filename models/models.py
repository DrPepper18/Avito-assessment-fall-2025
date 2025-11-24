from sqlalchemy.orm import declarative_base
from sqlalchemy import *
from datetime import datetime


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(BigInteger(), primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    isActive = Column(Boolean(), nullable=False, default=True)


class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(BigInteger(), primary_key=True, autoincrement=True)
    team_name = Column(String(50), unique=True, nullable=False, index=True)


class TeamMember(Base):
    __tablename__ = 'teammembers'
    
    team_id = Column(BigInteger(), ForeignKey('teams.id'), nullable=False, index=True)
    member_id = Column(BigInteger(), ForeignKey('users.id'), nullable=False, index=True)
    
    __table_args__ = (
        PrimaryKeyConstraint('team_id', 'member_id'),
    )


class PullRequest(Base):
    __tablename__ = 'pullrequests'
    
    id = Column(BigInteger(), primary_key=True, autoincrement=True)
    pull_request_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    author_id = Column(BigInteger(), ForeignKey('users.id'), nullable=False, index=True)
    isMerged = Column(Boolean(), nullable=False, default=False)
    createdAt = Column(DateTime, nullable=True, default=datetime.utcnow)
    mergedAt = Column(DateTime, nullable=True)


class Reviewers(Base):
    __tablename__ = 'reviewers'
    
    pr_id = Column(BigInteger(), ForeignKey('pullrequests.id'), nullable=False, index=True)
    reviewer_id = Column(BigInteger(), ForeignKey('users.id'), nullable=False, index=True)
    
    __table_args__ = (
        PrimaryKeyConstraint('pr_id', 'reviewer_id'),
    )
