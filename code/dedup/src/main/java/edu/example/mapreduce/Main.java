package edu.example.mapreduce;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

/**
 * Entry point for running either the default wordcount or the dedup MapReduce job.
 */
public class Main {

    public static void main(String[] args) throws Exception {

        System.out.println("==== Main args ====");
        System.out.println("args.length = " + args.length);
        for (int i = 0; i < args.length; i++) {
            System.out.println("args[" + i + "] = " + args[i]);
        }
        System.out.println("===================");

        String inputPath;
        String outputPath;
        if (args.length >= 2) {
            inputPath = args[0];
            outputPath = args[1];
        } else {
            System.err.println("WARN: 参数数量不是 2，使用默认 HDFS 路径");
            inputPath = "/mr_input";
            outputPath = "/mr_output_01";
        }

        Configuration conf = new Configuration();
        conf.setFloat("mapreduce.job.reduce.slowstart.completedmaps", 1.0f);

        Job job = Job.getInstance(conf, "DedupExperiment");
        job.setJarByClass(Main.class);

        job.setMapperClass(DedupMapper.class);
        job.setReducerClass(DedupReducer.class);
        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(NullWritable.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(NullWritable.class);

        // Force a fixed number of reducers for more stable experiment runs
        job.setNumReduceTasks(4);
        
        FileInputFormat.addInputPath(job, new Path(inputPath));
        FileOutputFormat.setOutputPath(job, new Path(outputPath));

        boolean success = job.waitForCompletion(true);
        System.exit(success ? 0 : 1);
    }
}
