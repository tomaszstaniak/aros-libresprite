/* Diagnostic, not shipped: report mutex unlocks by a task that does not hold
 * the mutex. AROS pthread NORMAL mutexes and SDL mutexes call
 * ReleaseSemaphore without checking the owner, and exec then raises
 * "Semaphore in an illegal state". Link with
 *   -Wl,--wrap=pthread_mutex_unlock -Wl,--wrap=SDL_UnlockMutex
 * Each bad unlock appends the call stack to RAM:unlock-check.log, with the
 * run-time address of a reference function so the host can map addresses
 * back to symbols (nm/addr2line on the unstripped executable).
 */
#include <exec/semaphores.h>
#include <exec/tasks.h>
#include <proto/exec.h>
#include <pthread.h>
#include <stdio.h>
#include <unwind.h>

struct SDL_Mutex;

int __real_pthread_mutex_unlock(pthread_mutex_t *mutex);
void __real_SDL_UnlockMutex(struct SDL_Mutex *mutex);
int __wrap_pthread_mutex_unlock(pthread_mutex_t *mutex);
void __wrap_SDL_UnlockMutex(struct SDL_Mutex *mutex);

static int reports;

struct trace {
    void *pc[24];
    int n;
};

static _Unwind_Reason_Code collect(struct _Unwind_Context *ctx, void *arg)
{
    struct trace *t = arg;
    if (t->n >= 24)
        return _URC_END_OF_STACK;
    t->pc[t->n++] = (void *)_Unwind_GetIP(ctx);
    return _URC_NO_REASON;
}

static void report(const char *what, struct SignalSemaphore *sem)
{
    struct trace t = { { 0 }, 0 };
    FILE *f;

    if (reports >= 20)
        return;
    reports++;
    _Unwind_Backtrace(collect, &t);
    f = fopen("RAM:unlock-check.log", "a");
    if (!f)
        return;
    fprintf(f, "%s by task %p (%s), owner %p, nest %d; ref __wrap_pthread_mutex_unlock=%p\n",
            what, (void *)FindTask(NULL), FindTask(NULL)->tc_Node.ln_Name ? FindTask(NULL)->tc_Node.ln_Name : "?",
            (void *)sem->ss_Owner, (int)sem->ss_NestCount, (void *)__wrap_pthread_mutex_unlock);
    for (int i = 0; i < t.n; i++)
        fprintf(f, "  #%d %p\n", i, t.pc[i]);
    fclose(f);
}

static int not_mine(struct SignalSemaphore *sem)
{
    return sem->ss_NestCount <= 0 || sem->ss_Owner != FindTask(NULL);
}

int __wrap_pthread_mutex_unlock(pthread_mutex_t *mutex)
{
    if (mutex && not_mine((struct SignalSemaphore *)&mutex->semaphore))
        report("pthread_mutex_unlock", (struct SignalSemaphore *)&mutex->semaphore);
    return __real_pthread_mutex_unlock(mutex);
}

/* SDL's AROS mutex is a bare SignalSemaphore (src/thread/aros/SDL_sysmutex.c). */
void __wrap_SDL_UnlockMutex(struct SDL_Mutex *mutex)
{
    if (mutex && not_mine((struct SignalSemaphore *)mutex))
        report("SDL_UnlockMutex", (struct SignalSemaphore *)mutex);
    __real_SDL_UnlockMutex(mutex);
}
