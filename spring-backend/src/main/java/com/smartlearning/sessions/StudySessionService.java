package com.smartlearning.sessions;

import com.smartlearning.tasks.Task;
import com.smartlearning.tasks.TaskService;
import com.smartlearning.tasks.TaskStatus;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class StudySessionService {

    private final StudySessionRepository repository;
    private final TaskService taskService;

    public StudySessionService(StudySessionRepository repository, TaskService taskService) {
        this.repository = repository;
        this.taskService = taskService;
    }

    @Transactional
    public StudySessionResponse create(UUID userId, CreateSessionRequest request) {
        if (request.taskId() != null) {
            taskService.getOwnedTask(userId, request.taskId());
        }

        StudySession session = new StudySession();
        session.setUserId(userId);
        session.setTaskId(request.taskId());
        session.setPlannedMode(request.plannedMode());
        session.setStartedAt(request.startedAt());
        session.setNotes(request.notes());

        return StudySessionResponse.from(repository.save(session));
    }

    @Transactional(readOnly = true)
    public List<StudySessionResponse> list(
            UUID userId,
            OffsetDateTime dateFrom,
            OffsetDateTime dateTo,
            int offset,
            int limit
    ) {
        Pageable pageable = PageRequest.of(offset / limit, limit);
        List<StudySession> sessions;

        if (dateFrom != null && dateTo != null) {
            sessions = repository.findByUserIdAndStartedAtGreaterThanEqualAndStartedAtLessThanEqualOrderByStartedAtDesc(
                    userId, dateFrom, dateTo, pageable
            );
        } else {
            sessions = repository.findByUserIdOrderByStartedAtDesc(userId, pageable);
        }

        return sessions.stream().map(StudySessionResponse::from).toList();
    }

    @Transactional(readOnly = true)
    public StudySession getOwnedSession(UUID userId, UUID sessionId) {
        return repository.findBySessionIdAndUserId(sessionId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));
    }

    @Transactional(readOnly = true)
    public StudySessionResponse get(UUID userId, UUID sessionId) {
        return StudySessionResponse.from(getOwnedSession(userId, sessionId));
    }

    @Transactional
    public StudySessionResponse end(UUID userId, UUID sessionId, EndSessionRequest request) {
        StudySession session = getOwnedSession(userId, sessionId);

        if (session.getEndedAt() != null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Session already ended");
        }

        if (request.endedAt().isBefore(session.getStartedAt())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "ended_at must be >= started_at");
        }

        session.setEndedAt(request.endedAt());
        session.setEndReason(request.endReason() == null ? SessionEndReason.completed : request.endReason());
        if (request.notes() != null) {
            session.setNotes(request.notes());
        }

        if (session.getTaskId() != null) {
            Task task = taskService.getOwnedTask(userId, session.getTaskId());
            task.setStatus(TaskStatus.done);
        }

        return StudySessionResponse.from(repository.save(session));
    }
}
