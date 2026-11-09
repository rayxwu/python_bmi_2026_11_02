import unittest

from app import BMI_CATEGORIES, GAUGE_MAX, GAUGE_MIN, NAME_MAX_LENGTH, app, bmi_gauge, bmi_guidance


class BmiAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_initial_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("了解自己的<br><em>健康狀況。GOGOGO!!</em>", page)
        self.assertIn("計算你的 BMI", page)
        self.assertNotIn('class="gauge"', page)
        self.assertNotIn('class="risk-list"', page)

    def test_calculation_and_advice(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("22.5", page)
        self.assertIn("健康體位", page)
        self.assertIn("維持均衡飲食", page)

    def test_result_page_renders_gauge_and_risk_reminders(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn('class="gauge"', page)
        self.assertIn("--needle-angle: -22.5deg", page)
        self.assertIn('class="gauge-segment tone-healthy is-active"', page)
        self.assertEqual(page.count("is-active"), 2)  # 作用中的色帶與其名稱標籤
        for name in ("過輕", "正常", "過重", "肥胖"):
            self.assertIn(">%s</text>" % name, page)
        for boundary in ("15", "18.5", "24", "27", "35"):
            self.assertIn(">%s</text>" % boundary, page)
        self.assertIn("健康風險 較低", page)
        self.assertIn('<h3 class="risk-title">', page)
        self.assertIn('class="risk-list"', page)
        self.assertIn("<li>BMI 無法反映體脂肪與肌肉量", page)
        self.assertNotIn("超出儀表板刻度範圍", page)

    def test_gauge_tone_and_risk_badge_follow_category(self):
        for height, weight, tone, badge in [
            ("170", "50", "low", "健康風險 中等"),
            ("170", "72", "high", "健康風險 中等"),
            ("170", "90", "obese", "健康風險 較高"),
        ]:
            with self.subTest(tone=tone):
                page = self.client.post("/", data={"height": height, "weight": weight}).get_data(as_text=True)
                self.assertIn('class="result-panel %s"' % tone, page)
                self.assertIn('class="gauge-segment tone-%s is-active"' % tone, page)
                self.assertIn(badge, page)

    def test_out_of_scale_bmi_clamps_needle_and_explains(self):
        response = self.client.post("/", data={"height": "170", "weight": "130"})
        page = response.get_data(as_text=True)
        self.assertIn("45.0", page)
        self.assertIn("--needle-angle: 90.0deg", page)
        self.assertIn("超出儀表板刻度範圍", page)
        self.assertIn("肥胖", page)

    def test_taiwan_adult_thresholds(self):
        for bmi, category in [
            (18.4, "體重過輕"),
            (18.5, "健康體位"),
            (23.9, "健康體位"),
            (24.0, "體重過重"),
            (26.9, "體重過重"),
            (27.0, "肥胖"),
        ]:
            with self.subTest(bmi=bmi):
                self.assertEqual(bmi_guidance(bmi)["label"], category)

    def test_every_category_has_advice_and_risk_reminders(self):
        for category in BMI_CATEGORIES:
            with self.subTest(category=category["key"]):
                guidance = bmi_guidance(16 if category["key"] == "underweight" else (category["upper"] or 40) - 0.1)
                self.assertEqual(guidance["key"], category["key"])
                self.assertTrue(guidance["advice"])
                self.assertTrue(guidance["risk_level"])
                self.assertIn(guidance["risk_level_key"], {"low", "moderate", "high"})
                self.assertGreaterEqual(len(guidance["risks"]), 2)

    def test_guidance_returns_a_copy(self):
        guidance = bmi_guidance(22)
        guidance["label"] = "changed"
        self.assertEqual(bmi_guidance(22)["label"], "健康體位")

    def test_invalid_fields_do_not_produce_result(self):
        for height, weight in [("", "65"), ("0", "65"), ("abc", "65"), ("170", "-2"), ("inf", "65"), ("170", "nan"), ("1e-300", "65"), ("1e308", "65"), ("1", "1e308")]:
            with self.subTest(height=height, weight=weight):
                response = self.client.post("/", data={"height": height, "weight": weight})
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-invalid="true"', page)
                self.assertNotIn("YOUR RESULT", page)
                self.assertNotIn('class="gauge"', page)

    def test_input_is_escaped(self):
        response = self.client.post("/", data={"height": '<script>alert(1)</script>', "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        self.assertIn("請輸入大於 0", page)

    def test_initial_page_has_optional_name_field(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('<label for="name">姓名 <span>NAME</span></label>', page)
        self.assertIn('id="name" name="name" type="text" autocomplete="name" maxlength="%d"' % NAME_MAX_LENGTH, page)
        self.assertIn('<span class="unit">選填</span>', page)

    def test_name_is_shown_in_health_advice(self):
        response = self.client.post("/", data={"name": "王小明", "height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<h2 id="result-title">給<span class="user-name">王小明</span>的健康建議</h2>', page)
        self.assertIn('value="王小明"', page)
        self.assertIn("維持均衡飲食", page)

    def test_advice_title_without_name_stays_generic(self):
        for name in (None, "", "   "):
            with self.subTest(name=name):
                data = {"height": "170", "weight": "65"}
                if name is not None:
                    data["name"] = name
                page = self.client.post("/", data=data).get_data(as_text=True)
                self.assertIn('<h2 id="result-title">給你的健康建議</h2>', page)
                self.assertNotIn('class="user-name"', page)

    def test_name_whitespace_is_normalized(self):
        page = self.client.post("/", data={"name": "  Ray \t\n Wu  ", "height": "170", "weight": "65"}).get_data(as_text=True)
        self.assertIn('<span class="user-name">Ray Wu</span>', page)
        self.assertIn('value="Ray Wu"', page)

    def test_name_is_escaped(self):
        page = self.client.post("/", data={"name": '"><script>alert(1)</script>', "height": "170", "weight": "65"}).get_data(as_text=True)
        self.assertNotIn("<script>", page)
        self.assertIn('value="&#34;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"', page)
        self.assertIn('<span class="user-name">&#34;&gt;&lt;script&gt;alert(1)&lt;/script&gt;</span>', page)

    def test_name_length_limit(self):
        page = self.client.post("/", data={"name": "王" * NAME_MAX_LENGTH, "height": "170", "weight": "65"}).get_data(as_text=True)
        self.assertIn('<span class="user-name">%s</span>' % ("王" * NAME_MAX_LENGTH), page)

        response = self.client.post("/", data={"name": "王" * (NAME_MAX_LENGTH + 1), "height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-invalid="true" aria-describedby="name-error"', page)
        self.assertIn("姓名請勿超過 %d 個字。" % NAME_MAX_LENGTH, page)
        self.assertNotIn("YOUR RESULT", page)
        self.assertIn('value="170"', page)
        self.assertIn('value="65"', page)

    def test_name_is_kept_when_other_fields_are_invalid(self):
        page = self.client.post("/", data={"name": "王小明", "height": "", "weight": "65"}).get_data(as_text=True)
        self.assertIn('value="王小明"', page)
        self.assertIn('aria-describedby="height-error"', page)
        self.assertNotIn('aria-describedby="name-error"', page)
        self.assertNotIn("YOUR RESULT", page)


class BmiGaugeTests(unittest.TestCase):
    def test_needle_angle_is_linear_across_scale(self):
        for bmi, angle in [(15, -90.0), (18.5, -58.5), (22.5, -22.5), (24, -9.0), (25, 0.0), (27, 18.0), (35, 90.0)]:
            with self.subTest(bmi=bmi):
                gauge = bmi_gauge(bmi)
                self.assertAlmostEqual(gauge["needle_angle"], angle)
                self.assertFalse(gauge["clamped"])

    def test_needle_is_clamped_outside_scale(self):
        low = bmi_gauge(GAUGE_MIN - 5)
        high = bmi_gauge(GAUGE_MAX + 10)
        self.assertEqual((low["needle_angle"], low["clamped"], low["active_key"]), (-90.0, True, "underweight"))
        self.assertEqual((high["needle_angle"], high["clamped"], high["active_key"]), (90.0, True, "obese"))

    def test_segments_match_categories_in_order(self):
        gauge = bmi_gauge(22.5)
        self.assertEqual([segment["key"] for segment in gauge["segments"]], [category["key"] for category in BMI_CATEGORIES])
        self.assertEqual([segment["label"] for segment in gauge["segments"]], ["過輕", "正常", "過重", "肥胖"])
        self.assertEqual(len({segment["tone"] for segment in gauge["segments"]}), 4)
        for segment in gauge["segments"]:
            self.assertRegex(segment["path"], r"^M [\d.]+ [\d.]+ A 140 140 0 0 1 [\d.]+ [\d.]+$")

    def test_segments_span_the_whole_scale_without_overlap(self):
        gauge = bmi_gauge(22.5)
        endpoints = []
        for segment in gauge["segments"]:
            parts = segment["path"].split()
            endpoints.append(((float(parts[1]), float(parts[2])), (float(parts[-2]), float(parts[-1]))))
        self.assertEqual(endpoints[0][0], (60.0, 190.0))
        self.assertEqual(endpoints[-1][1], (340.0, 190.0))
        for (_, end), (start, _) in zip(endpoints, endpoints[1:]):
            self.assertLess(end[0], start[0])  # 相鄰色帶之間保留間隙且依序排列

    def test_active_segment_follows_thresholds(self):
        for bmi, key in [(18.4, "underweight"), (18.5, "healthy"), (23.9, "healthy"), (24.0, "overweight"), (26.9, "overweight"), (27.0, "obese")]:
            with self.subTest(bmi=bmi):
                self.assertEqual(bmi_gauge(bmi)["active_key"], key)

    def test_ticks_and_labels_cover_scale_and_thresholds(self):
        gauge = bmi_gauge(22.5)
        self.assertEqual(len(gauge["ticks"]), GAUGE_MAX - GAUGE_MIN + 1 + 1)  # 每個整數一個刻度，18.5 另加一個主刻度
        self.assertEqual(sum(tick["major"] for tick in gauge["ticks"]), 3)
        value_labels = [label["text"] for label in gauge["labels"] if label["kind"] == "value"]
        self.assertEqual(value_labels, ["15", "18.5", "24", "27", "35"])
        name_labels = [label["key"] for label in gauge["labels"] if label["kind"] == "name"]
        self.assertEqual(name_labels, ["underweight", "healthy", "overweight", "obese"])


if __name__ == "__main__":
    unittest.main()
