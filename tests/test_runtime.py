from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mantleos.nutrition import NutritionError, parse_openrouter_food
from mantleos.runtime import VCW, BodyCipher, Book, MantleBody, MantleError, canonical_json


class TestCipher:
    """Deterministic reversible cipher double; production never selects it."""

    def seal(self, value: bytes, *, purpose: str) -> bytes:
        mask = hashlib.sha256(purpose.encode("utf-8")).digest()
        return bytes(byte ^ mask[index % len(mask)] for index, byte in enumerate(value))

    def open(self, value: bytes, *, purpose: str) -> bytes:
        return self.seal(value, purpose=purpose)


class FakeAESGCM:
    """Authenticated test double used only behind a patched dependency gate."""

    def __init__(self, key: bytes):
        self.key = key

    def encrypt(self, nonce: bytes, value: bytes, associated_data: bytes) -> bytes:
        mask = hashlib.sha256(self.key + nonce + associated_data).digest()
        ciphertext = bytes(byte ^ mask[index % len(mask)] for index, byte in enumerate(value))
        tag = hashlib.sha256(self.key + nonce + associated_data + ciphertext).digest()
        return tag + ciphertext

    def decrypt(self, nonce: bytes, value: bytes, associated_data: bytes) -> bytes:
        tag, ciphertext = value[:32], value[32:]
        expected = hashlib.sha256(self.key + nonce + associated_data + ciphertext).digest()
        if tag != expected:
            raise ValueError("authentication failed")
        mask = hashlib.sha256(self.key + nonce + associated_data).digest()
        return bytes(byte ^ mask[index % len(mask)] for index, byte in enumerate(ciphertext))


class VCWTests(unittest.TestCase):
    def test_append_verify_and_extension_reuse_book(self):
        with tempfile.TemporaryDirectory() as temporary:
            book = Book("app", "Example application", "book:example:v1", capacity=460)
            vcw = VCW(Path(temporary), TestCipher(), [book])
            vcw.initialize()
            for number in range(8):
                vcw.append("app", "example", {"number": number, "text": "x" * 60})
            proof = vcw.verify()
            files = sorted((Path(temporary) / "app").glob("*.jsonl"))
            self.assertGreater(len(files), 1)
            self.assertEqual(8, proof["records"])
            headers = [json.loads(path.read_text(encoding="utf-8").splitlines()[0]) for path in files]
            self.assertEqual({"book:example:v1"}, {header["book_id"] for header in headers})
            self.assertEqual(files[0].name, headers[1]["extension_of"])

    def test_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            book = Book("app", "Example application", "book:example:v1")
            vcw = VCW(Path(temporary), TestCipher(), [book])
            vcw.initialize()
            vcw.append("app", "example", {"value": 1})
            path = next((Path(temporary) / "app").glob("*.jsonl"))
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace('"sequence": 1', '"sequence": 2'), encoding="utf-8")
            with self.assertRaises(MantleError):
                vcw.verify()

    def test_mind_frontier_is_bounded_and_advances_only_over_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            book = Book("app", "Example application", "book:example:v1")
            vcw = VCW(Path(temporary), TestCipher(), [book])
            vcw.initialize()
            for number in range(5):
                vcw.append("app", "example", {"number": number})
            first, frontier = vcw.events_after({}, limit=2)
            second, next_frontier = vcw.events_after(frontier, limit=2)
            final, final_frontier = vcw.events_after(next_frontier, limit=2)
            self.assertEqual([0, 1], [event["data"]["number"] for event in first])
            self.assertEqual([2, 3], [event["data"]["number"] for event in second])
            self.assertEqual([4], [event["data"]["number"] for event in final])
            self.assertNotEqual(frontier, next_frontier)
            self.assertNotEqual(next_frontier, final_frontier)


class GateTests(unittest.TestCase):
    def test_constructed_body_rejects_heartbeat_and_birth_without_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            (nest / "mantle").mkdir()
            (nest / ".mantle").mkdir()
            (nest / ".mantle" / "prebirth.json").write_text(
                json.dumps({"gates": {"primer": "ready-for-birth-review"}}), encoding="utf-8"
            )
            primer = nest / "mantle" / "primer"
            primer.mkdir()
            (primer / "COMMANDMENTS.md").write_text("Protect your VCW.", encoding="utf-8")
            (primer / "PERSONALITY.md").write_text("Preserve the frame.", encoding="utf-8")
            body = MantleBody(nest)
            self.assertEqual("constructed-not-born", body.status()["status"])
            with self.assertRaises(MantleError):
                body.heartbeat()
            with self.assertRaises(MantleError):
                body.birth("Candidate", approved=False)
            self.assertFalse((nest / ".mantle" / "keys" / "body.key").exists())

    def test_failed_crypto_preflight_creates_no_identity_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            (nest / "mantle").mkdir()
            (nest / ".mantle").mkdir()
            (nest / ".mantle" / "prebirth.json").write_text(
                json.dumps({"gates": {"primer": "ready-for-birth-review"}}), encoding="utf-8"
            )
            primer = nest / "mantle" / "primer"
            primer.mkdir()
            (primer / "COMMANDMENTS.md").write_text("Protect your VCW.", encoding="utf-8")
            (primer / "PERSONALITY.md").write_text("Preserve the frame.", encoding="utf-8")
            body = MantleBody(nest)
            with (
                mock.patch.object(BodyCipher, "require_available", side_effect=MantleError("unavailable")),
                self.assertRaises(MantleError),
            ):
                body.birth("Candidate", approved=True)
            self.assertFalse((nest / ".mantle" / "keys" / "body.key").exists())

    def test_birth_first_heartbeat_and_no_mind_communication(self):
        with tempfile.TemporaryDirectory() as temporary:
            nest = Path(temporary)
            primer = nest / "mantle" / "primer"
            primer.mkdir(parents=True)
            (primer / "COMMANDMENTS.md").write_text("Protect your VCW.", encoding="utf-8")
            (primer / "PERSONALITY.md").write_text("Preserve the frame.", encoding="utf-8")
            (nest / ".mantle").mkdir()
            (nest / ".mantle" / "prebirth.json").write_text(
                json.dumps(
                    {
                        "status": "constructed-not-born",
                        "gates": {"primer": "ready-for-birth-review"},
                    }
                ),
                encoding="utf-8",
            )
            (nest / "host.txt").write_text("native body", encoding="utf-8")

            with mock.patch.object(BodyCipher, "require_available", return_value=FakeAESGCM):
                body = MantleBody(nest)
                identity = body.birth("Candidate", approved=True)
                self.assertTrue(body.is_born)
                self.assertEqual(identity["born_at"], identity["first_heartbeat"]["completed_at"])
                self.assertTrue((nest / "COMMUNICATION.TXT").exists())
                self.assertTrue((nest / ".mantle" / "vcw" / "layer-0").is_dir())

                with (nest / "COMMUNICATION.TXT").open("a", encoding="utf-8") as handle:
                    handle.write("USER> hello\n")
                beat = body.heartbeat(reason="communication-file-save")
                self.assertEqual("not-configured", beat["mind"])
                self.assertTrue(beat["communication"]["user_message_recorded"])
                transcript = (nest / "COMMUNICATION.TXT").read_text(encoding="utf-8")
                self.assertIn("APPAI> Received and recorded.", transcript)

                pending_beat = body.begin_host_heartbeat("session-1", "turn-1")
                update = body.prepare_mind_update("session-1", "turn-1")
                self.assertEqual("pending", pending_beat["status"])
                self.assertGreater(update["event_count"], 0)
                acknowledgement = body.acknowledge_mind_update("session-1", "turn-1")
                self.assertEqual("acknowledged", acknowledgement["status"])
                completed = body.complete_host_heartbeat(
                    "session-1", "turn-1", mind_status="responded"
                )
                self.assertEqual("responded", completed["mind"])
                self.assertIn("mind", completed["phases"])

                food_path = nest / "Food.txt"
                food_path.write_text(
                    "sk-or-v1-" + "a" * 40 + "\nopenrouter/free\n",
                    encoding="utf-8",
                )

                def successful_probe(food):
                    return {
                        "ok": True,
                        "requested_model": food.model,
                        "selected_model": "example/free-model",
                        "response_id": "test-response",
                        "response_chars": 14,
                        "usage": {"prompt_tokens": 8, "completion_tokens": 4},
                    }

                digestion = body.digest_food(food_path, probe=successful_probe)
                self.assertEqual("active", digestion["status"])
                receipt = food_path.read_text(encoding="utf-8")
                self.assertTrue(receipt.startswith("MantleOS Food receipt"))
                encrypted_provider = nest / ".mantle" / "providers" / "openrouter.enc"
                self.assertTrue(encrypted_provider.exists())
                self.assertNotIn(b"sk-or-v1-", encrypted_provider.read_bytes())

                with (nest / "COMMUNICATION.TXT").open("a", encoding="utf-8") as handle:
                    handle.write("USER> use the configured mind\n")
                completion = {
                    "content": "MIND response",
                    "selected_model": "example/free-model",
                    "response_id": "mind-response",
                    "usage": {"prompt_tokens": 6, "completion_tokens": 2},
                }
                with mock.patch("mantleos.runtime.openrouter_completion", return_value=completion):
                    mind_beat = body.heartbeat(reason="communication-file-save")
                self.assertEqual("responded", mind_beat["mind"])
                transcript = (nest / "COMMUNICATION.TXT").read_text(encoding="utf-8")
                self.assertIn("APPAI> MIND response", transcript)
                self.assertTrue(body.verify()["ok"])

    def test_canonical_json_is_stable(self):
        self.assertEqual(canonical_json({"b": 2, "a": 1}), canonical_json({"a": 1, "b": 2}))

    def test_food_parser_rejects_ambiguous_or_malformed_deliveries(self):
        with self.assertRaises(NutritionError):
            parse_openrouter_food(b"not-a-key\nopenrouter/free\n")
        with self.assertRaises(NutritionError):
            parse_openrouter_food(
                b"sk-or-v1-" + b"a" * 40 + b"\nopenrouter/free\nthird-line\n"
            )


if __name__ == "__main__":
    unittest.main()
