/*
 * TCalc - High-performance native scientific calculator
 * Copyright (C) 2026 Tahsin Önemli
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#pragma once

#include <poll.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

#include <csignal>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "calc/pub/calculator.hpp"
#include "internal/test_helpers.hpp"

/// How a smoke call ended. A math error is what the app shows the user, so it is allowed.
enum class SmokeOutcome : std::uint8_t { Returned, MathError, OtherException };

struct SmokeResult {
    SmokeOutcome outcome;
    std::string detail;
};

/// Run one call and classify how it ended; the only rule a smoke case is judged by.
template <typename Fn> SmokeResult run_guarded(Fn &&fn) {
    try {
        std::forward<Fn>(fn)();
        return {SmokeOutcome::Returned, {}};
    } catch (const CalculatorError &) {
        return {SmokeOutcome::MathError, {}};
    } catch (const std::exception &e) {
        return {SmokeOutcome::OtherException, e.what()};
    } catch (...) {
        return {SmokeOutcome::OtherException, "unknown exception"};
    }
}

/// In-process smoke case: a value or a math error passes, anything else fails.
template <typename Fn> void smoke_allow_math_error(TestContext &ctx, const char *name, Fn &&fn) {
    test_detail::with_case(ctx, name, [&] {
        const SmokeResult r = run_guarded(std::forward<Fn>(fn));
        EXPECT_MSG(ctx, r.outcome != SmokeOutcome::OtherException, [&](auto &os) {
            os << "unexpected exception: " << r.detail;
        });
    });
}

/// Why an isolated case failed: an abort or a freeze kills the child, an exception does not.
enum class CaseFault : std::uint8_t { Abort, Freeze, Exception };

struct CaseFailure {
    std::size_t index;
    CaseFault fault;
    std::string detail;
};

struct IsolatedRun {
    std::vector<CaseFailure> failures;
    std::optional<std::string> setup_error;
};

namespace smoke_detail {

inline void write_all(int fd, const std::string &line) {
    std::size_t done = 0;
    while (done < line.size()) {
        const ssize_t n = ::write(fd, line.data() + done, line.size() - done);
        if (n <= 0)
            ::_exit(3);
        done += static_cast<std::size_t>(n);
    }
}

inline std::string one_line(std::string s) {
    for (auto &ch : s)
        if (ch == '\n')
            ch = ' ';
    return s;
}

/// The child announces each case before it runs it and never touches the parent's output.
template <typename RunCase>
[[noreturn]] void child(int fd, std::size_t first, std::size_t count, RunCase &run_case) {
    // A core dump takes longer than a case may, so the abort would read as a freeze. 1, not 0:
    // Linux ignores a 0 limit when core_pattern is a pipe (systemd-coredump) and skips it on 1.
    const rlimit no_core{1, 1};
    ::setrlimit(RLIMIT_CORE, &no_core);
    for (std::size_t i = first; i < count; ++i) {
        write_all(fd, "S " + std::to_string(i) + "\n");
        const SmokeResult r = run_guarded([&] { run_case(i); });
        if (r.outcome == SmokeOutcome::OtherException)
            write_all(fd, "E " + std::to_string(i) + " " + one_line(r.detail) + "\n");
    }
    write_all(fd, "D\n");
    ::_exit(0);
}

inline std::string death(int status) {
    if (WIFSIGNALED(status))
        return "signal " + std::to_string(WTERMSIG(status));
    return "exit " + std::to_string(WEXITSTATUS(status));
}

} // namespace smoke_detail

/// Run `count` cases in forked children, `run_case(i)` each. A child that dies or stops answering
/// for `limit_ms` is blamed on the last case it announced, and a new child goes on after it.
template <typename RunCase>
IsolatedRun run_isolated(std::size_t count, int limit_ms, RunCase run_case) {
    IsolatedRun out;
    std::size_t next = 0;
    while (next < count) {
        int fds[2];
        if (::pipe(fds) != 0) {
            out.setup_error = "pipe failed";
            return out;
        }
        const pid_t pid = ::fork();
        if (pid < 0) {
            out.setup_error = "fork failed";
            return out;
        }
        if (pid == 0) {
            ::close(fds[0]);
            smoke_detail::child(fds[1], next, count, run_case);
        }
        ::close(fds[1]);

        std::optional<std::size_t> last;
        std::string buf;
        bool finished = false;
        bool froze = false;
        while (!finished) {
            pollfd p{fds[0], POLLIN, 0};
            if (::poll(&p, 1, limit_ms) == 0) {
                ::kill(pid, SIGKILL);
                froze = true;
                break;
            }
            char chunk[4096];
            const ssize_t n = ::read(fds[0], chunk, sizeof chunk);
            if (n <= 0)
                break;
            buf.append(chunk, static_cast<std::size_t>(n));
            std::size_t nl = 0;
            while ((nl = buf.find('\n')) != std::string::npos) {
                const std::string line = buf.substr(0, nl);
                buf.erase(0, nl + 1);
                if (line == "D") {
                    finished = true;
                } else if (line.starts_with("S ")) {
                    last = std::stoul(line.substr(2));
                } else if (line.starts_with("E ")) {
                    const auto sp = line.find(' ', 2);
                    out.failures.push_back(
                        {std::stoul(line.substr(2, sp - 2)),
                         CaseFault::Exception,
                         line.substr(sp + 1)});
                }
            }
        }
        ::close(fds[0]);
        int status = 0;
        ::waitpid(pid, &status, 0);
        if (finished)
            break;
        if (!last) {
            out.setup_error = "child ended before its first case: " + smoke_detail::death(status);
            return out;
        }
        if (froze)
            out.failures.push_back({*last, CaseFault::Freeze, {}});
        else
            out.failures.push_back({*last, CaseFault::Abort, smoke_detail::death(status)});
        next = *last + 1;
    }
    return out;
}
