"""Short, parameterized transactions; optimistic per-conversation revision checks."""

from uuid import uuid4

from sqlalchemy import and_, case, func, insert, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError

from app.agent.schemas import AgentResponse
from app.memory.context import ContextTurn
from app.memory.tables import conversations, messages, turns


class MemoryUnavailableError(RuntimeError):
    pass


class ConversationNotFound(ValueError):
    pass


class ConversationConflict(ValueError):
    pass


class ConversationRepository:
    def __init__(self, engine):
        self.engine = engine

    def replay(self, request_id, request_hash, conversation_id):
        try:
            with self.engine.connect() as connection:
                row = connection.execute(select(turns.c.request_hash, turns.c.conversation_id,
                    messages.c.metadata).join(messages, and_(messages.c.request_id == turns.c.request_id,
                    messages.c.role == "assistant")).where(turns.c.request_id == request_id)).mappings().first()
            if row is None:
                return None
            if row["request_hash"] != request_hash or (conversation_id and row["conversation_id"] != conversation_id):
                raise ConversationConflict("Request ID is already associated with another request.")
            return AgentResponse.model_validate(row["metadata"])
        except (SQLAlchemyError, ValidationError):
            raise MemoryUnavailableError() from None

    def snapshot(self, conversation_id, max_turns: int, max_chars: int):
        if conversation_id is None:
            return uuid4(), None, []
        try:
            with self.engine.begin() as connection:
                revision = connection.scalar(select(conversations.c.revision).where(
                    conversations.c.id == conversation_id).with_for_update(read=True))
                if revision is None:
                    raise ConversationNotFound()
                user = messages.alias("user_message")
                assistant = messages.alias("assistant_message")
                rows = connection.execute(select(user.c.content,
                    assistant.c.metadata["resolved_message"].astext.label("resolved_message"),
                    assistant.c.metadata["capability"].astext.label("capability"),
                    assistant.c.metadata["status"].astext.label("status"))
                    .select_from(turns.join(user, and_(user.c.request_id == turns.c.request_id, user.c.role == "user"))
                        .join(assistant, and_(assistant.c.request_id == turns.c.request_id, assistant.c.role == "assistant")))
                    .where(turns.c.conversation_id == conversation_id)
                    .order_by(turns.c.turn_number.desc()).limit(max_turns)).mappings().all()
            history = []
            used = 0
            for row in rows:
                resolved = row["resolved_message"] or row["content"]
                cost = len(row["content"]) + len(resolved)
                if used + cost > max_chars:
                    break
                used += cost
                history.append(ContextTurn(row["content"], resolved, row["capability"], row["status"]))
            return conversation_id, revision, list(reversed(history))
        except SQLAlchemyError:
            raise MemoryUnavailableError() from None

    def commit_turn(self, conversation_id, revision, request_id, request_hash, request, response):
        try:
            with self.engine.begin() as connection:
                if revision is None:
                    connection.execute(insert(conversations).values(id=conversation_id, revision=0))
                number = connection.scalar(update(conversations).where(
                    conversations.c.id == conversation_id,
                    conversations.c.revision == (revision if revision is not None else 0),
                ).values(revision=conversations.c.revision + 1, updated_at=func.now()).returning(conversations.c.revision))
                if number is None:
                    raise ConversationConflict("Conversation changed. Retry the request.")
                connection.execute(insert(turns).values(request_id=request_id, conversation_id=conversation_id,
                    turn_number=number, request_hash=request_hash))
                content = response.answer or (response.assessment.interpretation if response.assessment else
                                               response.error.message if response.error else response.status)
                connection.execute(insert(messages), [
                    {"conversation_id": conversation_id, "request_id": request_id, "role": "user",
                     "content": request.message, "metadata": {"likelihood": request.likelihood,
                         "impact": request.impact, "top_k": request.top_k}},
                    {"conversation_id": conversation_id, "request_id": request_id, "role": "assistant",
                     "content": content, "metadata": response.model_dump(mode="json")},
                ])
            return response
        except IntegrityError:
            replay = self.replay(request_id, request_hash, request.conversation_id)
            if replay is not None:
                return replay
            raise MemoryUnavailableError() from None
        except ConversationConflict:
            replay = self.replay(request_id, request_hash, request.conversation_id)
            if replay is not None:
                return replay
            raise ConversationConflict("Conversation changed. Retry the request.") from None
        except SQLAlchemyError:
            raise MemoryUnavailableError() from None

    def history(self, conversation_id, limit: int, before_turn: int | None):
        try:
            with self.engine.connect() as connection:
                if connection.scalar(select(conversations.c.id).where(conversations.c.id == conversation_id)) is None:
                    raise ConversationNotFound()
                query = select(turns.c.request_id, turns.c.turn_number).where(turns.c.conversation_id == conversation_id)
                if before_turn is not None:
                    query = query.where(turns.c.turn_number < before_turn)
                recent = connection.execute(query.order_by(turns.c.turn_number.desc()).limit(limit + 1)).all()
                has_more = len(recent) > limit
                selected = recent[:limit]
                rows = connection.execute(select(messages, turns.c.turn_number).join(turns,
                    messages.c.request_id == turns.c.request_id).where(
                        messages.c.conversation_id == conversation_id,
                        messages.c.request_id.in_([row.request_id for row in selected]))
                    .order_by(turns.c.turn_number, case((messages.c.role == "user", 0), else_=1))).mappings().all()
            return {"conversation_id": conversation_id, "messages": [dict(row) for row in rows],
                    "has_more": has_more, "next_before_turn": selected[-1].turn_number if has_more else None}
        except SQLAlchemyError:
            raise MemoryUnavailableError() from None
