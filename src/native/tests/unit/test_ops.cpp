#include "internal/test_helpers.hpp"
#include "parser/pub/ops.hpp"

#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

void unit_ops(TestContext &ctx) {
    using namespace tcalc::ops;

    const std::size_t op_count = static_cast<std::size_t>(OpId::Count);
    EXPECT_MSG(ctx, kOps.size() == op_count, [&](auto &os) {
        os << "kOps size mismatch: got " << kOps.size() << ", expected " << op_count;
    });

    std::vector<bool> seen(op_count, false);
    for (const auto &op : kOps) {
        const auto idx = static_cast<std::size_t>(op.id);
        EXPECT_MSG(ctx, idx < op_count, [&](auto &os) {
            os << "op id out of range: " << idx << " >= " << op_count;
        });

        if (idx < op_count) {
            EXPECT_MSG(
                ctx, !seen[idx], [&](auto &os) { os << "duplicate op id in kOps: " << idx; });

            seen[idx] = true;
            EXPECT_MSG(
                ctx, !op.symbol.empty(), [&](auto &os) { os << "op symbol empty for id " << idx; });
            EXPECT_MSG(
                ctx, !op.method.empty(), [&](auto &os) { os << "op method empty for id " << idx; });
        }
    }

    for (std::size_t i = 0; i < op_count; i++) {
        const auto *spec = op_spec(static_cast<OpId>(i));
        EXPECT_MSG(ctx, spec != nullptr, [&](auto &os) { os << "op_spec missing for id " << i; });

        if (spec) {
            EXPECT_MSG(ctx, spec->id == static_cast<OpId>(i), [&](auto &os) {
                os << "op_spec id mismatch for id " << i;
            });
        }
    }

    std::unordered_map<std::string_view, const OpSpec *> tokens;
    for (const auto &entry : kTokenTable) {
        EXPECT_TRUE(ctx, !entry.token.empty(), "token table contains empty token");
        EXPECT_TRUE(ctx, entry.spec != nullptr, "token table contains null spec");

        if (!entry.token.empty() && entry.spec) {
            const auto [it, inserted] = tokens.emplace(entry.token, entry.spec);

            if (!inserted) {
                EXPECT_MSG(ctx, inserted, [&](auto &os) {
                    os << "duplicate token '" << entry.token << "' for op " << entry.spec->method
                       << " (" << entry.spec->symbol << "), already used by op "
                       << it->second->method << " (" << it->second->symbol << ")";
                });
            }
        }
    }
}
