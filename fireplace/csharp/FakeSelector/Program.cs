using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;

namespace FakeSelector
{
	class LessThanSelector
	{
		private string attrname;
		private int attrvalue;

		public LessThanSelector(string attrname, int attrvalue) {
			this.attrname = attrname;
			this.attrvalue = attrvalue;
		}

		public List<Dictionary<string, int>> evaluate(List<Dictionary<string, int>> entities) {
			// For Linq, use:
			// return (from e in entities where e.ContainsKey(attrname) && e[attrname] < attrvalue select e).ToList();

			// For foreach, use:
			var n = new List<Dictionary<string, int>>();
			foreach (var e in entities)
				if (e.ContainsKey(attrname) && e[attrname] < attrvalue)
					n.Add(e);
			return n;
		}
	}

	class Program
	{
		static void Main(string[] args) {
			Random r = new Random();
			var c = "abcdefghijklmnopqrstuvwxyz";

			// Number of game entities
			var numObjects = new List<int> { 50, 100, 500, 1000 };

			// Number of selections to do
			var numIterations = new List<int> { 100, 500, 1000, 2000, 5000 };

			// Time taken (seconds)
			var timeTaken = new List<List<double>>();

			foreach (var objCount in numObjects) {
				// Create game entities
				var entities = new List<Dictionary<string, int>>();

				for (int i = 0; i < objCount; i++) {
					var entity = new Dictionary<string, int>();
					var attributes = r.Next(1, 6);

					for (int j = 0; j < attributes; j++)
						try {
							entity.Add(c[r.Next(0, 26)].ToString(), r.Next(1, 101));
						} catch (Exception) { }

					entities.Add(entity);
				}

				var times = new List<double>();

				// Selection criteria
				foreach (var iterCount in numIterations) {
					Console.WriteLine(objCount + " entities, " + iterCount + " selections");

					Stopwatch stopwatch = new Stopwatch();
					stopwatch.Start();

					var selector = new LessThanSelector("c", 50);

					for (int i = 0; i < iterCount; i++)
						selector.evaluate(entities);

					stopwatch.Stop();
					times.Add(stopwatch.Elapsed.TotalSeconds);
				}

				timeTaken.Add(times);
			}

			// Results
			string csvFile = "profile.csharp.foreach.csv";

			StringBuilder sb = new StringBuilder();
			foreach (var timeRow in timeTaken)
				sb.AppendLine(string.Join(",", timeRow));

			File.WriteAllText(csvFile, sb.ToString());
		}
	}
}
