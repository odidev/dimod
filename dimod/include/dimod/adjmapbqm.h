// Copyright 2020 D-Wave Systems Inc.
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

#ifndef DIMOD_ADJMAPBQM_H_
#define DIMOD_ADJMAPBQM_H_

#include <map>
#include <utility>
#include <vector>

#include "dimod/utils.h"

namespace dimod {

template<class V, class B>
class AdjMapBQM {
 public:
    using bias_type = B;
    using variable_type = V;
    using size_type = std::size_t;

    using outvars_iterator = typename std::map<V, B>::iterator;
    using const_outvars_iterator = typename std::map<V, B>::const_iterator;

    // in the future we'd probably like to make this protected
    std::vector<std::pair<std::map<V, B>, B>> adj;

    AdjMapBQM() {}

    template<class BQM>
    explicit AdjMapBQM(const BQM &bqm) {
        adj.resize(bqm.num_variables());

        for (variable_type v = 0; v < bqm.num_variables(); ++v) {
            set_linear(v, bqm.get_linear(v));

            auto span = bqm.neighborhood(v);
            adj[v].first.insert(span.first, span.second);
        }
    }

    /// Add one (disconnected) variable to the BQM and return its index.
    variable_type add_variable() {
        adj.resize(adj.size()+1);
        return adj.size()-1;
    }

    /// Get the degree of variable `v`.
    size_type degree(variable_type v) {
        return adj[v].first.size();
    }

    bias_type get_linear(variable_type v) const {
        return adj[v].second;
    }

    std::pair<bias_type, bool> get_quadratic(variable_type u, variable_type v) {
        assert(u >= 0 && u < adj.size());
        assert(v >= 0 && v < adj.size());
        assert(u != v);

        auto it = adj[u].first.find(v);

        if (it == adj[u].first.end() || it->first != v)
            return std::make_pair(0, false);

        return std::make_pair(it->second, true);
    }

    std::pair<outvars_iterator, outvars_iterator>
    neighborhood(variable_type u) {
        assert(u >= 0 && u < invars.size());
        return std::make_pair(adj[u].first.begin(), adj[u].first.end());
    }

    std::pair<const_outvars_iterator, const_outvars_iterator>
    neighborhood(variable_type u) const {
        assert(u >= 0 && u < invars.size());
        return std::make_pair(adj[u].first.cbegin(), adj[u].first.cend());
    }

    size_type num_variables() const {
        return adj.size();
    }

    size_type num_interactions() const {
        size_type count = 0;
        for (auto it = adj.begin(); it != adj.end(); ++it)
            count += it->first.size();
        return count / 2;
    }

    variable_type pop_variable() {
        assert(adj.size() > 0);

        variable_type v = adj.size() - 1;

        // remove v from all of its neighbor's neighborhoods
        for (auto it = adj[v].first.cbegin(); it != adj[v].first.cend(); ++it)
            adj[it->first].first.erase(v);

        adj.pop_back();

        return adj.size();
    }

    bool remove_interaction(variable_type u, variable_type v) {
        assert(u >= 0 && u < adj.size());
        assert(v >= 0 && v < adj.size());

        if (adj[u].first.erase(v) > 0) {
            adj[v].first.erase(u);
            return true;
        }

        return false;
    }

    void set_linear(variable_type v, bias_type b) {
        assert(v >= 0 && v < invars.size());
        adj[v].second = b;
    }

    bool set_quadratic(variable_type u, variable_type v, bias_type b) {
        assert(u >= 0 && u < adj.size());
        assert(v >= 0 && v < adj.size());
        assert(u != v);

        adj[u].first[v] = b;
        adj[v].first[u] = b;

        // to be consistent with AdjArrayBQM, we return whether the value was
        // set
        return true;
    }
};

}  // namespace dimod

#endif  // DIMOD_ADJMAPBQM_H_
