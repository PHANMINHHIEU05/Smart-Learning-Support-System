package com.smartlearning.blocks;

import com.smartlearning.sessions.StudySessionService;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class SessionBlockService {

    private final SessionBlockRepository repository;
    private final StudySessionService studySessionService;

    public SessionBlockService(SessionBlockRepository repository, StudySessionService studySessionService) {
        this.repository = repository;
        this.studySessionService = studySessionService;
    }

    @Transactional
    public SessionBlockResponse create(UUID userId, CreateBlockRequest request) {
        studySessionService.getOwnedSession(userId, request.sessionId());
        validateEndAfterStart(request.startAt(), request.endAt(), "end_at must be >= start_at");

        repository.findFirstBySessionIdOrderByStartAtDesc(request.sessionId()).ifPresent(lastBlock -> {
            if (lastBlock.getEndAt() == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Previous block has not ended");
            }
            if (request.startAt().isBefore(lastBlock.getEndAt())) {
                throw new ResponseStatusException(
                        HttpStatus.UNPROCESSABLE_ENTITY,
                        "start_at must be >= previous block end_at"
                );
            }
        });

        SessionBlock block = new SessionBlock();
        block.setSessionId(request.sessionId());
        block.setBlockType(request.blockType());
        block.setStartAt(request.startAt());
        block.setEndAt(request.endAt());
        block.setPlannedDurationSeconds(request.plannedDurationSeconds());

        return SessionBlockResponse.from(repository.save(block));
    }

    @Transactional(readOnly = true)
    public List<SessionBlockResponse> listBySession(UUID userId, UUID sessionId) {
        studySessionService.getOwnedSession(userId, sessionId);
        return repository.findBySessionIdOrderByStartAtAsc(sessionId)
                .stream()
                .map(SessionBlockResponse::from)
                .toList();
    }

    @Transactional
    public SessionBlockResponse heartbeat(UUID userId, UUID blockId, BlockHeartbeatRequest request) {
        SessionBlock block = getOwnedBlock(userId, blockId);
        OffsetDateTime endedAt = request.endedAt() == null ? OffsetDateTime.now() : request.endedAt();
        updateEndAtIfLater(block, endedAt);
        return SessionBlockResponse.from(repository.save(block));
    }

    @Transactional
    public void closeLatest(UUID userId, UUID sessionId) {
        studySessionService.getOwnedSession(userId, sessionId);
        repository.findFirstBySessionIdOrderByStartAtDesc(sessionId)
                .ifPresent(block -> {
                    updateEndAtIfLater(block, OffsetDateTime.now());
                    repository.save(block);
                });
    }

    private SessionBlock getOwnedBlock(UUID userId, UUID blockId) {
        SessionBlock block = repository.findByBlockId(blockId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Block not found"));
        studySessionService.getOwnedSession(userId, block.getSessionId());
        return block;
    }

    private static void updateEndAtIfLater(SessionBlock block, OffsetDateTime endedAt) {
        validateEndAfterStart(block.getStartAt(), endedAt, "ended_at must be >= start_at");
        if (block.getEndAt() == null || endedAt.isAfter(block.getEndAt())) {
            block.setEndAt(endedAt);
        }
    }

    private static void validateEndAfterStart(OffsetDateTime startAt, OffsetDateTime endAt, String message) {
        if (endAt != null && endAt.isBefore(startAt)) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, message);
        }
    }
}
