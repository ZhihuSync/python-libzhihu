#!/usr/bin/env python
#coding: utf8

import sqlalchemy
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


# Dict type.
import json
from sqlalchemy.ext import mutable

class Dict(sqlalchemy.TypeDecorator):
  impl = sqlalchemy.String

  def process_bind_param(self, value, dialect):
    return json.dumps(value)

  def process_result_value(self, value, dialect):
    return json.loads(value)

mutable.MutableDict.associate_with(Dict)



Base = declarative_base()

class People(Base):
    __tablename__ = 'people'
    uuid  = Column(String(32), primary_key=True) # Hash ID
    token = Column(String, nullable=False)
    name  = Column(String(250), nullable=False)
    avatar= Column(String, nullable=False)
    gender= Column(String(10), nullable=False) # male / female
    bio   = Column(String, nullable=False)
    sns   = Column(Dict, nullable=True)
    descp = Column(String, nullable=True)


class Question(Base):
    __tablename__ = 'question'
    uuid = Column(Integer, primary_key=True)
    id   = Column(Integer, primary_key=True)
    token = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    content = Column(String(250), nullable=False)


class Answer(Base):
    __tablename__ = 'answer'
    # Here we define columns for the table address.
    # Notice that each column is also a normal Python instance attribute.
    uuid = Column(Integer, primary_key=True)
    id = Column(Integer, primary_key=True)
    token = Column(String(250))

    street_name = Column(String(250))
    street_number = Column(String(250))
    post_code = Column(String(250), nullable=False)
    
    question_id = Column(Integer, ForeignKey('question.id'))
    question_uuid = Column(Integer, ForeignKey('question.uuid'))

    people_uuid = Column(Integer, ForeignKey('people.uuid'))
    # people_id = Column(Integer, ForeignKey('people.id'))
    content = Column(String(250))

    # person = relationship(Person)


class Comment(Base):
	__tablename__ = "comment"
	uuid = Column(String(250), primary_key=True, nullable=False)
	id = Column(Integer, primary_key=True, nullable=False)
	token = Column(String(250))
# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
engine = create_engine('sqlite:///sqlite.db')

# Create all tables in the engine. This is equivalent to "Create Table"
# statements in raw SQL.
Base.metadata.create_all(engine)


from sqlalchemy.orm import sessionmaker
Base.metadata.bind = engine


DBSession = sessionmaker(bind=engine)
session = DBSession()

# new_person = People(uuid=123, hash_id=1234, name=u"刘")
# session.add(new_person)
# session.commit()


