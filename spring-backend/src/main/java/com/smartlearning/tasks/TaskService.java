package com.smartlearning.tasks;

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
public class TaskService {

    private final TaskRepository repository;

    public TaskService(TaskRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public TaskResponse create(UUID userId, CreateTaskRequest request) {
        Task task = new Task();
        task.setUserId(userId);
        task.setTitle(request.title());
        task.setDescription(request.description());
        task.setStatus(request.status() == null ? TaskStatus.todo : request.status());
        task.setPriority(request.priority());
        task.setDueAt(request.dueAt());
        task.setEstimatedMinutes(request.estimatedMinutes());
        task.setSubjectName(request.subjectName());
        task.setTagsJson(request.tagsJson());

        return TaskResponse.from(repository.save(task));
    }

    @Transactional(readOnly = true)
    public List<TaskResponse> list(
            UUID userId,
            TaskStatus status,
            OffsetDateTime dueFrom,
            OffsetDateTime dueTo,
            int offset,
            int limit
    ) {
        Pageable pageable = PageRequest.of(offset / limit, limit);
        List<Task> tasks;

        if (status != null && dueFrom != null && dueTo != null) {
            tasks = repository.findByUserIdAndStatusAndDueAtGreaterThanEqualAndDueAtLessThanEqualOrderByCreatedAtDesc(
                    userId, status, dueFrom, dueTo, pageable
            );
        } else if (status != null) {
            tasks = repository.findByUserIdAndStatusOrderByCreatedAtDesc(userId, status, pageable);
        } else if (dueFrom != null && dueTo != null) {
            tasks = repository.findByUserIdAndDueAtGreaterThanEqualAndDueAtLessThanEqualOrderByCreatedAtDesc(
                    userId, dueFrom, dueTo, pageable
            );
        } else {
            tasks = repository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
        }

        return tasks.stream().map(TaskResponse::from).toList();
    }

    @Transactional(readOnly = true)
    public Task getOwnedTask(UUID userId, UUID taskId) {
        return repository.findByTaskIdAndUserId(taskId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Task not found"));
    }

    @Transactional(readOnly = true)
    public TaskResponse get(UUID userId, UUID taskId) {
        return TaskResponse.from(getOwnedTask(userId, taskId));
    }

    @Transactional
    public TaskResponse update(UUID userId, UUID taskId, UpdateTaskRequest request) {
        Task task = getOwnedTask(userId, taskId);

        if (request.title() != null) {
            task.setTitle(request.title());
        }
        if (request.description() != null) {
            task.setDescription(request.description());
        }
        if (request.status() != null) {
            task.setStatus(request.status());
        }
        if (request.priority() != null) {
            task.setPriority(request.priority());
        }
        if (request.dueAt() != null) {
            task.setDueAt(request.dueAt());
        }
        if (request.estimatedMinutes() != null) {
            task.setEstimatedMinutes(request.estimatedMinutes());
        }
        if (request.subjectName() != null) {
            task.setSubjectName(request.subjectName());
        }
        if (request.tagsJson() != null) {
            task.setTagsJson(request.tagsJson());
        }

        return TaskResponse.from(repository.save(task));
    }

    @Transactional
    public void delete(UUID userId, UUID taskId) {
        Task task = getOwnedTask(userId, taskId);
        repository.delete(task);
    }
}
