#pragma once
#include <string>
#include <unordered_map>
#include "value.hpp"

namespace tcalc::eval {

class VarStore {
  public:
    [[nodiscard]] const Value *get(const std::string &name) const {
        const auto it = vars_.find(name);
        return it == vars_.end() ? nullptr : &it->second;
    }
    void set(const std::string &name, Value v) { vars_[name] = std::move(v); }
    void unset(const std::string &name) { vars_.erase(name); }
    void clear() { vars_.clear(); }

  private:
    std::unordered_map<std::string, Value> vars_;
};

/// The one store, for now. Calculator tabs will key this on a session id; until then
/// there is a single store and nothing outside the evaluator touches it.
inline VarStore &session_vars() {
    static VarStore store;
    return store;
}

} // namespace tcalc::eval
