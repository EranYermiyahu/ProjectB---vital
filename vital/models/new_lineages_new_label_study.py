# %% [markdown]
# # Training covid models
# ### This notebook is an example usage of how to use the model alongside the covid-data-collector in order to train, evaluate and test the model
# #### In this notebook you will find example usages on how to use the core functionalities of the model 

# %% [markdown]
# #### Import third party modules, and also the data_collector: covid19_genome and the model module

# %%
import os
# os.environ["CUDA_VISIBLE_DEVICES"] = "-1" # Uncomment to disable GPU
import glob
import sys

from model import Model, DatasetName, load_model, remove_model

__ORIG_WD__ = os.getcwd()

sys.path.append(f"{__ORIG_WD__}/../data_collectors/")
os.chdir(f"{__ORIG_WD__}/../data_collectors/")
from covid19_genome import Covid19Genome

os.chdir(__ORIG_WD__)


# %% [markdown]
# #### Create a model, or try to load it, if it was already have been created.
# 
# In order to use the model, the first thing you have to do is provide it with a dataset (with the help of the data_collector). In the following cell you are provided with an example that create the dataset.
# 
# In this instance, we will load the lineages of the 10/1/2021 UShER tree. This notebook is created for the study of identifying new lineages.
# 
# You should note that when you are creating the dataset, you are passing the dataset type. You can obtain the available dataset types in the system by calling the model class function ```get_ds_types()```

# %%
frag_len = 288
model_name = "covid19-new_lineages-new_labels"

try:
    model = load_model(model_name)
except Exception:
    covid19_genome = Covid19Genome()
    lineages = covid19_genome.getLocalLineages(512)
    lineages_set = set(lineages)
    
    # Decide lineages to train on (defined in the lineages_in_tree.txt file)
    lineages_in_tree = []
    with open("lineages_in_tree.txt", "r") as f:
        for line in f:
            lineage = line.split("\t")[0]
            if lineage in lineages_set:
                lineages_in_tree.append(lineage)
    print(f"The number of lineages located in the tree is: {len(lineages_in_tree)}")

    lineages_in_tree.sort()
    dataset = []
    def get_dataset():
        new_lineages = []
        lineages_in_tree_set = set(lineages_in_tree)
        for lineage in lineages:
            if lineage in lineages_in_tree_set:
                dataset.append((lineage, covid19_genome.getLocalAccessionsPath(lineage)))
            else:
                new_lineages += covid19_genome.getLocalAccessionsPath(lineage)[:64]
        dataset.append(("new_lineages", new_lineages))
        return dataset

    portions = {
        DatasetName.trainset.name: 0.8,
        DatasetName.validset.name: 0.1,
        DatasetName.testset.name: 0.1
    }

    dataset = get_dataset()
    
    model = Model(model_name)
    model.create_datasets(model.get_ds_types()[0], dataset, portions)

# %% [markdown]
# After you have created the model, and created its datasets. You can check which neural network structures is available. You can do that by calling the model class function ```get_ml_model_structure()```.
# 
# After you see all the ml_model structures available in the system, you can check which hyper parameters are needed to define each and every ml_model structure. This is done by calling the model class function ```get_ml_model_structure_hps()```. The ```get_ml_model_structure_hps()``` will return which hps are required, and what it their type.

# %%
print(model.get_ml_model_structures())
print(model.get_ml_model_structure_hps(model.get_ml_model_structures()[0]))

# %% [markdown]
# You can also see which properties help define the current type of dataset by calling to the model class function ```get_ds_props()``` This function could be called only after the dataset have been succesfully created. This function will return the properties of the dataset as well as their values.

# %%
print(model.get_ds_props())

ds_props = model.get_ds_props()
if not 'frag_len' in ds_props:
    raise Exception("No fragment length exist in the dataset props.")
model.update_ds_props({
    'frag_len': frag_len
})

# %% [markdown]
# A use case of the system with the VitStructure model and the minhash genome datasets (a.k.a. mh_genome_ds).
# 
# In the mh_genome_ds the coverage is a dataset property that sets the genome coverage rate.
# 
# In the VitStructure, the model_depth is the number of transformer encoders.
# 
# In this example use-case these two parameters will help us define a neural network that will be trained on the dataset (with the current coverage rate)

# %%
coverage = 4
ml_model_depth = 1
sequencer_instrument = "ideal"

# %%
sequencer_instrument_to_error_profile_map = {
    "ideal": {
        "substitution_rate": 0.0,
        "insertion_rate": 0.0,
        "deletion_rate": 0.0
    },
    "illumina": {
        "substitution_rate": 0.005,
        "insertion_rate": 0.001,
        "deletion_rate": 0.001
    },
    "ont": {
        "substitution_rate": 0.01,
        "insertion_rate": 0.04,
        "deletion_rate": 0.04
    },
    "pacbio": {
        "substitution_rate": 0.005,
        "insertion_rate": 0.025,
        "deletion_rate": 0.025
    },
    "roche": {
        "substitution_rate": 0.002,
        "insertion_rate": 0.01,
        "deletion_rate": 0.01
    }
}

def get_model_name(ml_model_depth, coverage, sequencer_instrument):
    if not sequencer_instrument in sequencer_instrument_to_error_profile_map:
        raise Exception(f"Invalid sequencer instrument: {sequencer_instrument}")
    return f"vit.{ml_model_depth}.{coverage}x.{sequencer_instrument}"

ml_model_name = get_model_name(ml_model_depth, coverage, sequencer_instrument)

# %% [markdown]
# #### Adding a new neural network
# 
# In this cell we will create an ml_model with the required hps (and also optional) as outputted earlier.

# %%
newly_added = True
try:
    model.add_ml_model(ml_model_name, hps={
        "structure": model.get_ml_model_structures()[0],
        "d_model": model.get_ds_props()["frag_len"],
        "d_val": 128,
        "d_key": 128,
        "heads": 8,
        "d_ff": 1024+256,
        "labels":  len(model.get_labels()),
        "activation": "relu",
        "optimizer": {
            "name": "AdamW",
            "params": {
                "learning_rate": 0.001,
            },
        },
        "encoder_repeats": ml_model_depth,
        "regularizer": {
            "name": "l2",
            "params": {
                "l2": 0.0001
            }
        },
        "dropout": 0.2,
    })
except:
    newly_added = False
    print("Model already exists")

# %%
models = model.list_ml_models()
print(models)

# %%
if newly_added:
    # assert False, "Please consider doing transfer learning"
    pass
# model.transfer(get_model_name(ml_model_depth, coverage * 2, sequencer_instrument), ml_model_name, False)

# %%
# model.change_ml_hps(ml_model_name, {
#     "regularizer": {
#         "name": "l2",
#         "params": {
#             "l2": 0.00005,
#         },
#     },
#     "optimizer": {
#         "name": "AdamW",
#         "params": {
#             "learning_rate": model.get_ml_hps(ml_model_name)["optimizer"]["params"]["learning_rate"] / 2,
#         },
#     },
# })

# %% [markdown]
# #### Updating the dataset coverage

# %%
model.update_ds_props({
    "coverage": coverage,
    } | sequencer_instrument_to_error_profile_map[sequencer_instrument])

# %% [markdown]
# #### Setting dataset batch size and training

# %%
model.set_ds_batch_size(512)
model.train(ml_model_name, epochs=1000)


