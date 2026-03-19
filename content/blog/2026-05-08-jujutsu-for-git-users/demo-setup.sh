#!/usr/bin/env bash
#
# Builds a linear 5-commit jj stack that demonstrates split, absorb, rebase,
# and conflicts. Idempotent: re-run to reset after rehearsing a demo.
#
# Stack (bottom -> top, all messages prefixed "DEMO:" so reset is targeted):
#   A  Add CalculatorScreen scaffold
#   B  Add CalculatorViewModel with display state
#   C  Add digit buttons             (intentional 4.dp -> absorb target)
#   D  Add operator buttons and tighten outer padding   (split target)
#   E  Add equals and clear logic
#   @  empty working copy with two uncommitted absorb-target hunks:
#        - CalculatorViewModel.kt:  MutableStateFlow("")   -> MutableStateFlow("0")   (-> B)
#        - CalculatorScreen.kt:     Arrangement.spacedBy(4.dp) -> 8.dp in DigitRow    (-> C)

set -euo pipefail

REPO_ROOT="/Users/jalmeida/tmp/tmp-firefox"
CALC_DIR="$REPO_ROOT/mobile/android/fenix/app/src/main/java/org/mozilla/fenix/calculator"

cd "$REPO_ROOT"

# --- Reset ----------------------------------------------------------------
# Abandon any previous DEMO commits and clear the working copy.
jj new main >/dev/null
DEMO_REVS="$(jj log --no-graph -r 'description(glob:"DEMO:*")' -T 'change_id ++ "\n"' 2>/dev/null || true)"
if [[ -n "$DEMO_REVS" ]]; then
  # Pass the full revset; jj abandons all matching revisions in one go.
  jj abandon -r 'description(glob:"DEMO:*")' >/dev/null
fi
rm -rf "$CALC_DIR"
mkdir -p "$CALC_DIR"

SCREEN="$CALC_DIR/CalculatorScreen.kt"
VM="$CALC_DIR/CalculatorViewModel.kt"

# --- Commit A: scaffold ---------------------------------------------------
jj describe -m "Add CalculatorScreen scaffold" >/dev/null

cat > "$SCREEN" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun CalculatorScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        Text(text = "Calculator")
    }
}
KOTLIN

# --- Commit B: ViewModel + wire display -----------------------------------
jj new -m "Add CalculatorViewModel with display state" >/dev/null

cat > "$VM" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class CalculatorViewModel : ViewModel() {
    private val _display = MutableStateFlow("")
    val display: StateFlow<String> = _display

    fun onDigit(digit: Int) {
        val current = _display.value
        _display.value = if (current == "0") digit.toString() else current + digit
    }
}
KOTLIN

cat > "$SCREEN" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun CalculatorScreen(viewModel: CalculatorViewModel = viewModel()) {
    val display by viewModel.display.collectAsState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        Text(text = display)
    }
}
KOTLIN

# --- Commit C: digit buttons (with absorb-target 4.dp) --------------------
jj new -m "Add digit buttons" >/dev/null

cat > "$SCREEN" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun CalculatorScreen(viewModel: CalculatorViewModel = viewModel()) {
    val display by viewModel.display.collectAsState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        Text(text = display)
        DigitRow(digits = listOf(7, 8, 9), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(4, 5, 6), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(1, 2, 3), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(0), onDigit = viewModel::onDigit)
    }
}

@Composable
private fun DigitRow(digits: List<Int>, onDigit: (Int) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        digits.forEach { digit ->
            Button(onClick = { onDigit(digit) }) {
                Text(text = digit.toString())
            }
        }
    }
}
KOTLIN

# --- Commit D: operator buttons + outer padding tweak (split target) ------
jj new -m "Add operator buttons and tighten outer padding" >/dev/null

cat > "$SCREEN" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun CalculatorScreen(viewModel: CalculatorViewModel = viewModel()) {
    val display by viewModel.display.collectAsState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
    ) {
        Text(text = display)
        DigitRow(digits = listOf(7, 8, 9), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(4, 5, 6), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(1, 2, 3), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(0), onDigit = viewModel::onDigit)
        OperatorRow(onOperator = viewModel::onOperator)
    }
}

@Composable
private fun DigitRow(digits: List<Int>, onDigit: (Int) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        digits.forEach { digit ->
            Button(onClick = { onDigit(digit) }) {
                Text(text = digit.toString())
            }
        }
    }
}

@Composable
private fun OperatorRow(onOperator: (Operator) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Operator.entries.forEach { op ->
            Button(onClick = { onOperator(op) }) {
                Text(text = op.symbol)
            }
        }
    }
}
KOTLIN

cat > "$VM" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

enum class Operator(val symbol: String) {
    Plus("+"),
    Minus("-"),
    Times("×"),
    Divide("÷"),
}

class CalculatorViewModel : ViewModel() {
    private val _display = MutableStateFlow("")
    val display: StateFlow<String> = _display

    private var pendingOperator: Operator? = null
    private var leftOperand: Double? = null

    fun onDigit(digit: Int) {
        val current = _display.value
        _display.value = if (current == "0") digit.toString() else current + digit
    }

    fun onOperator(operator: Operator) {
        leftOperand = _display.value.toDoubleOrNull()
        pendingOperator = operator
        _display.value = "0"
    }
}
KOTLIN

# --- Commit E: equals + clear --------------------------------------------
jj new -m "Add equals and clear logic" >/dev/null

cat > "$SCREEN" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun CalculatorScreen(viewModel: CalculatorViewModel = viewModel()) {
    val display by viewModel.display.collectAsState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
    ) {
        Text(text = display)
        DigitRow(digits = listOf(7, 8, 9), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(4, 5, 6), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(1, 2, 3), onDigit = viewModel::onDigit)
        DigitRow(digits = listOf(0), onDigit = viewModel::onDigit)
        OperatorRow(onOperator = viewModel::onOperator)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = viewModel::onEquals) { Text(text = "=") }
            Button(onClick = viewModel::onClear) { Text(text = "C") }
        }
    }
}

@Composable
private fun DigitRow(digits: List<Int>, onDigit: (Int) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        digits.forEach { digit ->
            Button(onClick = { onDigit(digit) }) {
                Text(text = digit.toString())
            }
        }
    }
}

@Composable
private fun OperatorRow(onOperator: (Operator) -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Operator.entries.forEach { op ->
            Button(onClick = { onOperator(op) }) {
                Text(text = op.symbol)
            }
        }
    }
}
KOTLIN

cat > "$VM" <<'KOTLIN'
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.fenix.calculator

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

enum class Operator(val symbol: String) {
    Plus("+"),
    Minus("-"),
    Times("×"),
    Divide("÷"),
}

class CalculatorViewModel : ViewModel() {
    private val _display = MutableStateFlow("")
    val display: StateFlow<String> = _display

    private var pendingOperator: Operator? = null
    private var leftOperand: Double? = null

    fun onDigit(digit: Int) {
        val current = _display.value
        _display.value = if (current == "0") digit.toString() else current + digit
    }

    fun onOperator(operator: Operator) {
        leftOperand = _display.value.toDoubleOrNull()
        pendingOperator = operator
        _display.value = "0"
    }

    fun onEquals() {
        val right = _display.value.toDoubleOrNull() ?: return
        val left = leftOperand ?: return
        val op = pendingOperator ?: return
        val result = when (op) {
            Operator.Plus -> left + right
            Operator.Minus -> left - right
            Operator.Times -> left * right
            Operator.Divide -> if (right == 0.0) Double.NaN else left / right
        }
        _display.value = formatResult(result)
        pendingOperator = null
        leftOperand = null
    }

    fun onClear() {
        _display.value = "0"
        pendingOperator = null
        leftOperand = null
    }

    private fun formatResult(value: Double): String {
        return if (value % 1.0 == 0.0) value.toLong().toString() else value.toString()
    }
}
KOTLIN

# --- Working copy: two absorb-target hunks --------------------------------
# Empty change on top of E so the WC diff is isolated and obvious.
jj new -m "wip small fixes (absorb me)" >/dev/null

# Fix 1: initial display "" -> "0"   (line introduced in commit B)
sed -i.bak 's/MutableStateFlow("")/MutableStateFlow("0")/' "$VM" && rm "$VM.bak"

# Fix 2: DigitRow spacing 4.dp -> 8.dp   (line introduced in commit C; the
# OperatorRow / equals-row spacedBy(8.dp) lines are unchanged so absorb can
# uniquely attribute the hunk to C, not D or E).
python3 - "$SCREEN" <<'PY'
import sys, re
path = sys.argv[1]
src = open(path).read()
# Replace only the spacedBy(4.dp) inside DigitRow.
pattern = re.compile(r'(private fun DigitRow.*?Arrangement\.spacedBy\()4\.dp', re.S)
new, n = pattern.subn(r'\g<1>8.dp', src)
assert n == 1, f"Expected exactly one DigitRow 4.dp match, got {n}"
open(path, 'w').write(new)
PY

# --- Summary --------------------------------------------------------------
echo
echo "Stack built. Current state:"
echo
jj log -r 'main..@'
echo
echo "Working-copy diff (absorb targets):"
jj diff --stat
